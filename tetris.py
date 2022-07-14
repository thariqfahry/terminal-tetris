import numpy as np, curses, time
from tetris_pieces import pieces
from random import choice

REFRESH_RATE_HZ = 120
FRAME_PERIOD = 1/REFRESH_RATE_HZ

class Tetris:
    def __init__(self, gridsizey = 20, gridsizex = 10, fall_period = 60):
        self.tickcount = 0

        self.gridsizey = gridsizey
        self.gridsizex = gridsizex
        self.fall_period = fall_period

        self.buffer_offset = 5
        self.buffer = np.zeros((gridsizey + self.buffer_offset, gridsizex), dtype = np.int32)
        self.fixed_pieces = np.zeros((gridsizey, gridsizex), dtype=np.int32)
        self.state = self.fixed_pieces.copy()

        self.spawn()

    def tick(self, command = None):
        self.increment_y, self.increment_x, self.rotate_increment = 0, 0, 0

        self.handle_input(command)
        self.advance_game_state()
        self.draw()

        self.tickcount +=1

    def spawn(self):
        self.active_piece = choice(pieces)

        self.active_piece_posy =  0
        self.unmoved_for = 0
        self.active_piece_posx = self.gridsizex//2

        self.rotate_state = 0
    
    def handle_input(self, command):
        move_amount_x_map = {None : 0, "LEFT" : -1, "RIGHT" : 1, "DOWN" : 0, "UP" : 0}
        self.increment_x = move_amount_x_map[command]

        if command == "DOWN":
            self.increment_y  = 1
        
        if command == "UP":
            self.rotate_increment = 1
            #TODO implement rotation w/ collision check
            #FIXME pieces sometimes freeze when trying to get them under an overhang
            
    def advance_game_state(self):
        
        #Move the active piece downwards every self.fall_period ticks.
        #In a single tick, the active piece is only ever allowed to move down
        #1 y-position, so even self.increment_y is already set to 1 due to 
        #a "DOWN" command, this will simply maintain that value
        #(and not increment to 2).
        if not self.tickcount % self.fall_period:
            self.increment_y = 1

        self.predraw_and_collision_check()

        self.unmoved_for = 0 if self.increment_y else self.unmoved_for + 1

        #TODO too high?
        if self.unmoved_for > self.fall_period*2 or self.active_piece_posy == 20:
            #TODO check top 5 rows of buffer for game over

            self.freeze_piece()
            #TODO check contiguous row for scoring
            self.spawn()

            self.unmoved_for = 0
        
    def predraw_and_collision_check(self):
        #Generate self.trimmed_buffer, but don't do anything with it yet.
        is_overlap = self.predraw(self.increment_y, self.increment_x, self.rotate_increment)

        #TODO preemptively check collisions FIRST so we know exactly what to allow
        #If an overlap exists, we have a collsion.
        if is_overlap:
            fixed_x = fixed_y = False
            if self.increment_x:
                if not self.predraw(self.increment_y, 0, self.rotate_increment):
                    self.increment_x = 0
                    fixed_x = True
                else:
                    fixed_x = False

            if self.increment_y:
                if not self.predraw(0, self.increment_x, self.rotate_increment):
                    self.increment_y = 0
                    fixed_y = True
                else:
                    fixed_y = False
            
            if not (fixed_x and fixed_y):
                self.predraw(0, 0, 0)
        
        self.active_piece_posy, self.active_piece_posx, self.rotate_state \
            = self.newy, self.newx, self.new_rotate_state
    
    def predraw(self, increment_y, increment_x, rotation):
        #Shorthand aliases for variables to make this section more readable,
        #and to create local copies of active_piece_posy, active_piece_posx, 
        #and active_piece (so that translation and rotation is undoable)
        y, x = self.active_piece_posy, self.active_piece_posx
        ap, bo = self.active_piece, self.buffer_offset

        #Increment active_piece's y-position by increment_y.
        self.newy = y = (y + increment_y) % (self.gridsizey + 1)

        #Increment (or decrement) active_piece's x position by increment_x.
        #We achieve 'wrapping' by shrinking the modulo operator by the piece's width.
        self.newx = x = (x + increment_x) % (self.gridsizex - self.active_piece.shape[1] + 1)         

        #Reset buffer.
        self.buffer[:] = 0

        #Rotate active_piece anticlockwise, rotation times - usually either 0 or 1
        self.new_rotate_state = (self.rotate_state + rotation) % 4
        ap = np.rot90(ap, self.new_rotate_state)

        #create the y-slice and x-slice Slice objects.
        ysl = slice(y - ap.shape[0] + bo, y + bo)
        xsl = slice(x, x + ap.shape[1])

        #Paste the active piece into the buffer.
        #FIXME a rotated piece will not warp because its x-pos is now wrong
        self.buffer[ysl, xsl] = ap

        #Trim the buffer's y-dimension to match the size of the game state grid
        self.trimmed_buffer = self.buffer[bo:]

        #Test if the trimmed_buffer overlaps fixed_pieces.
        is_overlap = np.bitwise_and(self.fixed_pieces, self.trimmed_buffer).any()
        return is_overlap

    def freeze_piece(self):
        self.fixed_pieces = np.bitwise_or(self.fixed_pieces, self.trimmed_buffer)

    def draw(self):
        self.state = np.bitwise_or(self.trimmed_buffer, self.fixed_pieces)


# if __name__ == "__main__":
def main():

    screen = curses.initscr()
    curses.noecho()
    screen.clear()
    screen.nodelay(True)
    screen.keypad(True)

    screen.addstr(23, 0, "Press q to quit")
    
    gridsizey, gridsizex = 20, 10
    game = Tetris(gridsizey, gridsizex, fall_period = int(0.5*REFRESH_RATE_HZ))
    d = np.zeros((gridsizey//2, gridsizex), dtype=np.int32)

    while True:
        key = None
        command = None

        try:
            key = screen.getkey()
            screen.addstr(21, 0, "         ")
            screen.addstr(21, 0, key)
        except curses.error:
            pass
        else:
            try:
                keymap = {  "KEY_B1":"LEFT", 
                            "KEY_B3":"RIGHT", 
                            "KEY_A2":"UP",
                            "KEY_C2":"DOWN",

                            "KEY_LEFT":"LEFT", 
                            "KEY_RIGHT":"RIGHT", 
                            "KEY_UP":"UP",
                            "KEY_DOWN":"DOWN"}

                command = keymap[key]
            except  KeyError:
                pass

            if key == 'q':
                break
            
        game.tick(command)

        s = game.state
        #TODO innefficient; maybe 
        # b = np.lib.stride_tricks.as_strided(a, (1000, a.size), (0, a.itemsize))
        for row, _ in enumerate(d):
            for col, __ in enumerate(_):
                if (s[(row*2):(row*2)+2,col] == np.array([0, 1])).all():
                    d[row,col] = 1
                elif (s[(row*2):(row*2)+2,col] == np.array([1, 0])).all():
                    d[row, col] = 2
                elif (s[(row*2):(row*2)+2,col] == np.array([1, 1])).all():
                    d[row,col] = 3
                elif (s[(row*2):(row*2)+2,col] == np.array([0, 0])).all():
                    d[row,col] = 0


        for index, row in enumerate(d):
            line = "".join(row.astype(str))
            line = line.replace("0", ' ').replace("1", "▄").replace("2","▀").replace("3","█")

            screen.addstr(index, 0, line)
        
        #debug
        screen.addstr(22, 0, "y=" + f"{game.active_piece_posy}".zfill(2))
        screen.addstr(21, 10, str(game.tickcount))

        screen.refresh()
        time.sleep(FRAME_PERIOD)

if __name__ == "__main__":
    main()
