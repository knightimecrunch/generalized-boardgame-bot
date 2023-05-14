# kivy imports
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.uix.image import Image as kvImage

# Screen capture imports, with goal of platform independance + multimonitor support
from functools import partial
from PIL import Image
from kivy.core.image import Image as CoreImage
from pynput import mouse
import mss
import mss.tools
import numpy as np
from kivy.graphics import texture
import io
import cv2
import os
from pathlib import Path

# Setting Widget Types of Classes for Kvlang Declarations
class SettingsScreen(Screen):
    pass
class ChessToolsView(Screen):
    pass
class ToolBar(BoxLayout):
    pass
class ToolsScreenManager(ScreenManager):
    pass

# Game Types : Chess, Checkers*, GO*
# *not implemented

# Chess engine imports
import SSIM_PIL as ssim

class Chess():
    @staticmethod
    def initialize_chess_images_cache():
        currentBoardImage = Board.getCurrentBoard()
        cv2.imshow("temp.png", currentBoardImage)

        # List of pieces in initial chessboard order
        piece_order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'] + ['pawn']*8 + ['empty']*32 + ['pawn']*8 + ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']

        # Get the tiles from the slice function
        tiles = Board.slice(8, currentBoardImage)

        # Ensure there are 64 pieces
        assert len(tiles) == len(piece_order), "Number of tiles does not match the number of chess pieces"

        # Create the cache/chess directory if it doesn't exist
        directory = "cache/chess"
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Save each tile with the corresponding piece name
        for idx, tile in enumerate(tiles):
            tile_name = piece_order[idx]
            filename = f"{directory}/{tile_name}_{idx}.png"
            print(filename)
            cv2.imwrite(filename, tile)

class Checkers():
    pass

class Go():
    pass

# App structure

class SplitBoardImagesView(GridLayout):
    main_instance = None
    def __init__(self, **kwargs):
        super(SplitBoardImagesView, self).__init__(**kwargs)
        self.cols = 1
        self.rows = 1

    def store(self):
        SplitBoardImagesView.main_instance = self

    def display_board(tiles, h, w):
        imageArray = SplitBoardImagesView.main_instance.ids["imageGrid"]
        imageArray.cols = w
        imageArray.rows = h
        imageArray.clear_widgets()
        for tile in tiles:
            tile = Board.openCVtoCoreImage(tile)
            imageArray.add_widget(kvImage(texture = tile.texture))

class Board:
    """
        Game-type agnostic class that manages off-screen board image data. 
    """
    # Buffer to hold current screen image
    memoryBuffer = io.BytesIO() 
    temp = Image.open("board.png")
    temp.save(memoryBuffer, format='png')

    currentBoardImage = cv2.imread("board.png")
    
    # Coordinates for on-screen for board
    topLeft = (0, 0)
    botRight = (100, 100)

    def write_screen_to_buffer(*args):
        """
            Runs continuously, called from application start.
        """
        topLeft = Board.topLeft
        botRight = Board.botRight
        sct = mss.mss()
        width = abs(topLeft[0] - botRight[0]) 
        height = abs(topLeft[1] - botRight[1]) 
        bounding_box = {'top': topLeft[1], 'left': topLeft[0], 'width': width, 'height': height}
        image = sct.grab(bounding_box)
        image = Image.frombytes("RGB", image.size, image.bgra, "raw", "BGRX") 
        image.save(Board.memoryBuffer, format='png') 


    @staticmethod
    def update(object, dt):
        """
            Redraws on-screen board 
        """
        Board.memoryBuffer.seek(0) #after writing return to 0 index of memory for reading
        captureCV2 = np.frombuffer(Board.memoryBuffer.getvalue(), dtype=np.uint8)
        captureCV2 = cv2.imdecode(captureCV2, cv2.IMREAD_ANYCOLOR)
        Board.currentBoardImage = captureCV2
        Board.processing(captureCV2) 
        processedCapture = Board.draw_grid(captureCV2, (8,8))
        capture = Board.openCVtoCoreImage(processedCapture)
        PrimaryScreen.update_board(object, capture.texture)

    @staticmethod
    def processing(boardImage):
        tileList = Board.slice(8, boardImage)
        SplitBoardImagesView.display_board(tileList, 8, 8)

    @staticmethod
    def openCVtoCoreImage(anOpenCV):
        is_success, buffer = cv2.imencode(".png", anOpenCV)
        tempBuffer = io.BytesIO(buffer)
        tempBuffer.seek(0)
        aCoreImage = CoreImage(io.BytesIO(tempBuffer.read()), ext='png')
        tempBuffer.close()
        return aCoreImage
    
    @staticmethod
    def draw_grid(img, grid_shape, color = (0, 0, 255), thickness = 1):
        h, w, _ = img.shape
        rows, cols = grid_shape
        dy, dx = h / rows, w / cols
        for x in np.linspace(start = dx, stop = w - dx, num = cols - 1):
            x = int(round(x))
            cv2.line(img, (x, 0), (x, h), color=color, thickness=thickness)
        for y in np.linspace(start = dy, stop = h - dy, num = rows - 1):
            y = int(round(y))
            cv2.line(img, (0, y), (w, y), color = color, thickness = thickness)
        return img

    @staticmethod
    def slice(nslices, boardImage = currentBoardImage):
        h, w, channels = boardImage.shape
        slicesY = [(h // nslices) * n for n in range(1, nslices + 1)]
        slicesX = [(w // nslices) * n for n in range(1, nslices + 1)]
        tiles = []
        prevX = 0 
        prevY = 0
        for y in slicesY:
            row = boardImage[prevY:y, :]
            prevY = y
            prevX = 0
            for x in slicesX:
                tile = row[:, prevX:x]
                tiles.append(tile)
                prevX = x
        return tiles
    
    def getCurrentBoard():
        Board.memoryBuffer.seek(0) #after writing return to 0 index of memory for reading
        captureCV2 = np.frombuffer(Board.memoryBuffer.getvalue(), dtype = np.uint8)
        captureCV2 = cv2.imdecode(captureCV2, cv2.IMREAD_ANYCOLOR)
        return captureCV2

class PrimaryScreen(Screen):
    """
        Screen containing the board, the segmented board, and the menu for the selected game.
    """
    def __init__(self, **kwargs):
        super(PrimaryScreen, self).__init__(**kwargs)
        Clock.schedule_interval(partial(Board.update, self), 0.25)

    def update_board(self, capture):
        self.ids['boardImage'].texture = capture

class Application(App):
    def on_click(x, y, button, pressed):
        if pressed:
            Board.topLeft = (x, y)
        print('{0} at {1}'.format('Pressed' if pressed else 'Released', (x, y)))
        if not pressed:
            Board.botRight = (x,y)
            Board.write_screen_to_buffer()
            return False
    
    def initialize_chess_images_cache():
        Chess.initialize_chess_images_cache()

    def start_listener(null): 
        with mouse.Listener(on_click=Application.on_click) as listener:
            listener.join() 

    def build(self):
        Clock.schedule_interval(Board.write_screen_to_buffer, 0.25)
        pass

if __name__ == '__main__':
    Application().run()


