
class Context:
    def __init__(
        self, father = None, end_char: str = None
    ):
        #Contexto superior
        self.meta = father
        #Diccionario de las variables y funciones declaradas
        self.table = {}
        #Caracter que indica si el comando terminó ex. ")", "]"
        self.end_char = end_char

    def search_var(self, name: str) -> str:
        #Obtiene el valor de la variable si está en el contexto actual
        value = self.table.get(name, None)
        
        if value is None:
            #Si hay un contexto superior...
            if self.meta is not None:
                #... Obtiene el valor de la variable si está en dicho contexto
                value = self.meta.search_var(name)

        #IMPORTANTE: Retorna "n" si es un número, "f-{num}" si es una función (donde {num} es el número de argumentos de la función)
        return value

    def add_var(self, name: str, value):
        self.table[name] = value

def prepare_text(path: str) -> list:
    with open(path, "r") as file:
        file_lines: list[str] = file.readlines()

    final_text = []
    i = 0
    while i < len(file_lines):
        line = file_lines[i]
        #Reemplazar tabulaciones por espacios
        line = line.replace("\t", " ")
        #[Caracter Especial] separar el ! con un espacio
        line = line.replace("!", "! ")
        #Reemplaza múltiples espacios consecutivos por solo uno
        line = " ".join(line.split())
        #Separa los paréntesis en nuevas lineas
        line = (
            line.replace("(", "\n(\n")
            .replace(")", "\n)\n")
            .replace("[", "\n[\n")
            .replace("]", "\n]\n")
        )
        #[Caso Especial] separar el block de la siguiente instrucción
        line = line.replace("BLOCK ", "BLOCK\n")

        for result in line.split("\n"):
            #Elimina las líneas vacías
            if result and any([j!=" " for j in result]):
                #Par (número de línea, comandos de la línea (separados por ' '))
                final_text.append((i + 1, result.split()))

        i += 1

    return final_text

def verify(filetext: list) -> bool:
    global context, actual_line
    #Número de la línea actual
    status_line = actual_line

    commands = filetext[status_line][1]

    cmdname = commands[0]
    cmdargs = commands[1:]

    if cmdname == "DEFINE":
        if len(cmdargs) == 2:
            name, value = cmdargs
            #El nombre debe estar en minúscula y no debe contener caracteres especiales,
            # tampoco puede empezar con ':' para no chocar con los parámetros de las funciones
            if (not name.islower()) or ("!" in name) or (name[0] == ":"): 
                return False
            #Si el valor a definir es un número (obligatoriamente positivo)
            if value.isdigit():
                context.add_var(name, "n")
            else:
                #Si está redefiniendo una variable (ex. DEFINE x 1 ... DEFINE y x)
                if context.search_var(value) == "n":
                    context.add_var(name, "n")
                else:
                    return False
        else:
            return False
    elif cmdname in ("MOVE", "RIGHT", "LEFT", "ROTATE", "DROP", "FREE", "PICK", "POP"):
        if len(cmdargs) == 1:
            value = cmdargs[0]
            #Si no es un dígito ni está llamando una variable
            if not (value.isdigit() or (context.search_var(value) == "n")):
                return False
        else:
            return False
    elif cmdname == "LOOK":
        if len(cmdargs) == 1:
            if cmdargs[0] not in ('N','E','W','S'):
                return False
        else:
            return False
    elif cmdname == "CHECK":
        if len(cmdargs) == 2:
            value = cmdargs[1]
            if not ((cmdargs[0] in ('C','B')) and 
                        (value.isdigit() or (context.search_var(value) == "n"))):
                    return False
        else:
            return False
    elif cmdname == "BLOCKEDP":
        ## BLOCKEDP no es un comando, es una variable booleana
        return False
    elif cmdname == "NOP":
        if len(cmdargs):
            return False
    elif cmdname == "TO":
        if len(cmdargs) == 0:
            return False
        name = cmdargs[0]
        parameters = cmdargs[1:]

        if (not name.islower()) or ("!" in name):
            return False
        #Se crea la "variable" pero con la notación f-{num} donde {num} es el 
        # número de parámetros que recibe
        context.add_var(name, F"f-{len(parameters)}")
        #OPEN nuevo contexto
        context = Context(context, "END")
        for i in parameters:
            #Los nombres de los parámetros deben seguir las normas de variables
            if (not i.islower()) or ("!" in i):
                return False
            #Los nombres de los parámetros DEBEN comenzar con ':'
            if not i[0] == ":":
                return False
            #Todos los parámetros se toman como números
            context.add_var(i,"n")
        #Revisa si abre 'OUTPUT'
        actual_line += 1
        if not filetext[status_line+1][1] == ["OUTPUT"]:
            return False
    elif context.search_var(cmdname):
        value = context.search_var(cmdname)
        ## NO se puede llamar una variable que no sea una función
        if value == "n":
            return False
        if value.startswith("f-"):
            numargs = int(value.split("-")[1])
        #Si se llama una función se debe verificar que se llame con el mismo
        # número de parámetros con el que se definió
        if len(cmdargs) != numargs:
            return False
        for i in cmdargs:
            if not (i.isdigit() or (context.search_var(i) == "n")):
                return False
    elif cmdname == "IF":
        #Ignora todos los ! al comienzo del valor booleano
        while cmdargs[0] == "!":
            del cmdargs[0]
        if cmdargs[0] == "BLOCKEDP":
            del cmdargs[0]
            if len(cmdargs):
                return False
        elif cmdargs[0] == "CHECK":
            del cmdargs[0]
            if len(cmdargs) == 2:    
                value = cmdargs[1]
                if not ((cmdargs[0] in ('C','B')) and 
                        (value.isdigit() or (context.search_var(value) == "n"))):
                    return False
            else:
                return False
        #Revisa si abre '['
        actual_line += 1
        if not filetext[status_line+1][1] == ["["]: 
            return False
        #OPEN nuevo contexto
        context = Context(context, "]")
    elif cmdname == "(":
        #Revisa si sigue un BLOCK o un REPEAT
        actual_line += 1
        cmdargs = filetext[status_line+1][1]
        if cmdargs[0] == "BLOCK":
            del cmdargs[0]
            if len(cmdargs): return False
            #OPEN nuevo contexto
            context = Context(context, ")")
        elif cmdargs[0] == "REPEAT":
            del cmdargs[0]
            if len(cmdargs) == 1:
                value = cmdargs[0]
                if not (value.isdigit() or (context.search_var(value) == "n")):
                    return False
            else:
                return False
            #OPEN nuevo contexto
            context = Context(context, ")")
            #Revisa si abre '['
            actual_line += 1
            if not filetext[status_line+2][1] == ["["]:
                return False
            #OPEN nuevo contexto
            context = Context(context, "]")
        else:
            return False
    elif cmdname == context.end_char:
        if len(cmdargs):
            return False
        #CLOSE contexto anterior
        context = context.meta
    else:
        return False

    return True


def parse(path: str):
    global context, actual_line
    filetext = prepare_text(path)
    actual_line = 0

    success = True

    while True:
        #Indica si el programa ha estado bien o ha fallado hasta el momento
        if success:
            #Indica si el programa ya terminó (si está en la última línea)
            if len(filetext) == actual_line:
                print("YES")
                break
            else:
                success = verify(filetext)
                #Suma 1 - Indica que pasa a la siguiente línea
                actual_line += 1
        else:
            print("NO")
            break

if __name__ == "__main__":
    global context, actual_line
    context = Context()
    parse("code_test.txt")
    input()
