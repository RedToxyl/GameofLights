# a program that plays Conways Game of Life on a 7*7 Grid and displays it on ws2811 LEDs

import rpi_ws281x
import time
import random


# LED strip configuration:
# this is taken direcly from the ws_281x library
LED_COUNT = 50        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

grid = rpi_ws281x.PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
grid.begin()


# switches Red and Green channels, as the LEDs used for this project (ws2811) apparently are channeled differenty
def striprgb(px, colour):
    grid.setPixelColorRGB(px, colour[1], colour[0], colour[2])

# defines some colours
white = (255, 255, 255)
red = (255, 0, 0)
blue = (0, 0, 255)
green = (0, 255, 0)
yellow = (255, 255, 0)
purple = (255, 0, 255)
cyan = (0, 255, 255)
orange = (255, 165, 0)
black = (0, 0, 0)

# assigns a colour to each state that a cell can be in
states = {"dead": orange, "alive": blue, "dying": red, "zombie": green, "off": black}

def status(colour):
    striprgb(49, colour)
    grid.show()

class Cell:
    def __init__(self, coords, state):
        self.coords = coords
        self.state = state
        self.newstate = state

    # this only works for 7*7 Grids, other sizes need other conversion functions; get_gridcoords takes the position of a cell and returns the corresponding LED id
    def get_gridcoords(self):
        x = self.coords[0]
        y = self.coords[1]
        # conversion for even columns
        if y % 2 == 0:
            return (7 * y) - x + 1 - 1
        # conversion for odd columns
        else:
            return (7 * y) - 7 + x - 1

    # this doesnt actually display the state, grid.show() is still needed
    def display_state(self):
        striprgb(self.get_gridcoords(), states[self.state])

    def change_state(self):
        self.state = self.newstate

    # checks which cells are considered neighbors
    def get_neighbors(self):
        x = self.coords[0]
        y = self.coords[1]
        neighbors = [cell for cell in cells if (cell.coords[0] in (x + 1, x, x - 1) and cell.coords[1] in (y + 1, y, y - 1)) and not cell.coords == self.coords]
        return neighbors


cells = []
# this is said when the grid has died/locked down, can be muted via the menu
message_griddead = "All cells are dead. How about some more?"
message_gridlocked = "This grid is locked down. Have a new one!"
mute = True

# this function creates a list with every cell object, the chance_init determines the chance for the starting object have a certain state
# this NEEDS to be called
def generate(chance_init=20):
    # the variable constant checks wether the cells have entered a stable position
    global gridlock
    gridlock = 0
    global cells
    cells = []
    # one cell object is created for every pixel
    for x in range(1, 8):
        for y in range(1, 8):
            if random.randint(1, 100) < chance_init:
                cells.append(Cell([x, y], "alive"))
            else:
                cells.append(Cell([x, y], "dead"))
    for cell in cells:
        cell.display_state()
    grid.show()

def getcode():
    gridcode = ""
    for cell in cells:
        if cell.state == "dead":
            gridcode = gridcode + "0"
        elif cell.state == "alive":
            gridcode = gridcode + "1"
    return gridcode

def turn():
    status(green)
    # 1 determine the state that each cell should have
    # this is the part where the rules of the game are determined
    for cell in cells:
        neighbors = cell.get_neighbors()
        neighbor_states = [neighbor.state for neighbor in neighbors]
        living_n = neighbor_states.count("alive")
        # TODO different options for the corner & edge cells
        if living_n < 2 or living_n > 3:
            cell.newstate = "dead"
        elif living_n == 2 and cell.state == "alive":
            cell.newstate = "alive"
        elif living_n == 3:
            cell.newstate = "alive"
    if all(cell.state == "dead" for cell in cells):
        striprgb(49, red)
        if not mute:
            print(message_griddead)
        generate()
        time.sleep(1)
        return None
    elif all(cell.state == cell.newstate for cell in cells):
        global gridlock
        gridlock = gridlock + 1
        if gridlock >= 3:
            striprgb(49, red)
            if not mute:
                print(message_gridlocked)
            generate()
            time.sleep(1)
            return None
    # 2 update the cell states
    for cell in cells:
        cell.change_state()
        cell.display_state()
    # show the new state
    grid.show()
    time.sleep(0.5)

# some menu functions are defined here, TODO move them to a seperate file

def command_quit():
    for cell in cells:
        cell.state = "off"
        cell.display_state()
        grid.show()
    endlight = [yellow, orange, red, black]
    for x in endlight:
        status(x)
        grid.show()
        time.sleep(0.1)
    quit()

def command_continue():
    return None

def command_getcode():
    print(f"This grid started with the code: {getcode()}")
    menu()

def command_entercode():
    # this takes a 49 long string from the user
    # every 1 becomes a living, every 0 a dead cell
    usercode = ""
    while not len(usercode) == 49:
        usercode = input("Please enter the code (or q to abort)!: ")
        if usercode == "q":
            menu()
            return None
    for i in range(49):
        if usercode[i] == "0":
            cells[i].state = "dead"
        elif usercode[i] == "1":
            cells[i].state = "alive"
    for cell in cells:
        cell.display_state()
        cell.newstate = "dead"
    grid.show()
    menu()

def command_restart():
    generate()
    menu()

def command_brightness():
    new_brightness = 0
    while not 0 < new_brightness < 256:
        new_brightness = input("Please enter a brightness between 1 & 255(q to abort): ")
        if new_brightness == "q":
            menu()
            return None
        try:
            new_brightness = int(new_brightness)
        except ValueError:
            print("This is not a number.")
            new_brightness = 0
    global LED_BRIGHTNESS
    global grid
    LED_BRIGHTNESS = new_brightness
    grid = rpi_ws281x.PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    grid.begin()
    for cell in cells:
        cell.display_state()
    grid.show()
    menu()

def command_mute():
    global mute
    mute = not mute
    menu()

def command_help():
    print(f"Valid commands are: {valid_commands}")
    menu()

def menu():
    status(purple)
    command = ""
    global valid_commands
    valid_commands = ["q", "c", "g", "e", "r", "b", "m", "h", "rc"]
    while command not in valid_commands:
        command = input("You have openend the menu. Enter your command: ")
    if command == "q":
        command_quit()
    elif command == "c":
        command_continue()
    elif command == "g":
        command_getcode()
    elif command == "e":
        command_entercode()
    elif command == "r":
        command_restart()
    elif command == "b":
        command_brightness()
    elif command == "m":
        command_mute()
    elif command == "h":
        command_help()
    elif command == "rc":
        generate()
        return None

status(purple)
# generates starts until the user confirms
ok = "n"
while not ok == "y":
    generate()
    ok = input("Is this acceptable? y/n")

mainloop = True
while mainloop:
    try:
        turn()
    except KeyboardInterrupt:
        menu()
