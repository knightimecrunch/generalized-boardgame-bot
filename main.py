# kivy imports
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.uix.image import Image as kvImage
from kivy.core.window import Window
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.image import Image
from kivy.uix.rst import RstDocument
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.properties import Property


# Screen capture imports, with goal of platform independance + multimonitor support
from functools import partial
from PIL import Image as PILImage
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
import gameboard
from gameboard import ChessBoardUI  # assuming you have this module

class ToolsScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(ChessToolsView())

class ChessToolsView(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = GridLayout(rows=3, cols=1)

        layout.add_widget(Button(text='Save Initial Chessboard', on_press=Application.initialize_chess_images_cache))
        layout.add_widget(Label(text='temp'))
        layout.add_widget(ChessToolsTabsView())
        self.add_widget(layout)

class ChessToolsTabsView(TabbedPanel):
    matrix_view = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        tileList = Core.slice(8, cv2.imread("board.png"))

        self.matrix_view = ImageMatrixView(8, 8, tileList)
        self.add_widget(TabbedPanelItem(content = self.matrix_view))
        self.add_widget(TabbedPanelItem(text='2', content=Label(text='Second tab content area')))
        self.add_widget(TabbedPanelItem(text='3', content=RstDocument(text='\\n'.join(("Hello world", "-----------", "You are in the third tab.")))))

class ToolBar(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rows = 1
        self.cols = 4
        self.size_hint_y = None
        self.size_hint_x = 0.3
        self.height = 30

        self.add_widget(Button(text="Settings", on_press=self.change_screen))
        self.add_widget(Button(text="Board", on_press=self.change_screen))
        self.add_widget(Button(text="Get Coords", on_release=Application.start_click_and_drag))

    def change_screen(self, instance):
        screen_name = instance.text.lower()  # Assuming the text of the button is the screen name
        direction = "right" if screen_name == "settings" else "left"
        self.parent.parent.children[0].transition = NoTransition()
        self.parent.parent.children[0].transition.direction = direction
        self.parent.parent.children[0].current = screen_name

class GameBoardView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        layout = GridLayout(rows=2, cols=1)
        layout.add_widget(ToggleButton(text='Read From Screen'))
        layout.add_widget(gameboard.ChessBoardUI(40))
        self.add_widget(layout)

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = GridLayout(cols=2)
        layout.add_widget(Button(text='Button'))
        self.add_widget(layout)

class PrimaryScreen(Screen):
    """
        Screen containing the board, the segmented board, and the menu for the selected game.
    """
    viewport = None

    def on_kv_post(self, base_widget):
        return super().on_kv_post(base_widget)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        PrimaryScreen.self = self
        layout = GridLayout(cols=4)
        layout.add_widget(GameBoardView())
        layout.add_widget(ToolsScreenManager())
        self.viewport = Image()
        layout.add_widget(self.viewport)
        self.add_widget(layout)

class ImageMatrixView(GridLayout):
    def __init__(self, w, h, tiles, **kwargs):
        super(ImageMatrixView, self).__init__(**kwargs)
        self.instance = self
        self.cols = w
        self.rows = h
        self.clear_widgets()
        for tile in tiles:
            tile = Core.openCVtoCoreImage(tile)
            self.add_widget(kvImage(texture = tile.texture))

class Core:
    # Buffer to hold current screen image
    memoryBuffer = io.BytesIO() 
    temp = PILImage.open("board.png")
    temp.save(memoryBuffer, format='png')

    currentBoardImage = cv2.imread("board.png")
    
    # Coordinates for on-screen for board
    topLeft = (0, 0)
    botRight = (100, 100)

    def board_loop(dt):
        Core.write_screen_to_buffer()
        Core.redraw_board()

    def write_screen_to_buffer(*args):
        """
            Copies the contents of the screen from the top left bound to the bottom right bound to memory.
        """
        if Core.topLeft == Core.botRight: # default out when no drag occurred
            Core.topLeft = (0, 0)
            Core.botRight = (100, 100)
        try:
            topLeft = Core.topLeft
            botRight = Core.botRight
            sct = mss.mss()
            width = abs(topLeft[0] - botRight[0]) 
            height = abs(topLeft[1] - botRight[1]) 
            bounding_box = {'top': topLeft[1], 'left': topLeft[0], 'width': width, 'height': height}
            image = sct.grab(bounding_box)
            image = PILImage.frombytes("RGB", image.size, image.bgra, "raw", "BGRX") 
            image.save(Core.memoryBuffer, format='png') 
        except:
            print("Invalid screen selection")
            
    @staticmethod
    def redraw_board():
        """
            Redraws on-screen board, adding a grid, re-read from memory is require from conversion to CoreImage.
        """
        # reads into CV2 to make image adjustments, might be faster to read directly to CoreImage
        Core.memoryBuffer.seek(0) #after writing return to 0 index of memory for reading
        captureCV2 = np.frombuffer(Core.memoryBuffer.getvalue(), dtype=np.uint8)
        captureCV2 = cv2.imdecode(captureCV2, cv2.IMREAD_ANYCOLOR)
        Core.currentBoardImage = captureCV2

        # draw to sliced board view
        # tileList = Core.slice(8, captureCV2)
        # ChessToolsTabsView.matrix_view = ImageMatrixView(8, 8, tileList)

        # draw to board viewport
        processedCapture = Core.draw_grid(captureCV2, (8,8))
        capture = Core.openCVtoCoreImage(processedCapture)
        App.get_running_app().primary_screen.viewport.texture = capture.texture

    @staticmethod
    def draw_grid(img, grid_shape, color = (0, 0, 255), thickness = 1):
        h, w, _ = img.shape
        rows, cols = grid_shape
        dy, dx = h / rows, w / cols
        for x in np.linspace(start = dx, stop = w - dx, num = cols - 1):
            x = int(round(x))
            cv2.line(img, (x, 0), (x, h), color = color, thickness = thickness)
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
    
    @staticmethod
    def openCVtoCoreImage(anOpenCV):
        is_success, buffer = cv2.imencode(".png", anOpenCV)
        tempBuffer = io.BytesIO(buffer)
        tempBuffer.seek(0)
        aCoreImage = CoreImage(io.BytesIO(tempBuffer.read()), ext='png')
        tempBuffer.close()
        return aCoreImage
    
    def get_board_as_CV2():
        Core.memoryBuffer.seek(0)
        captureCV2 = np.frombuffer(Core.memoryBuffer.getvalue(), dtype = np.uint8)
        return cv2.imdecode(captureCV2, cv2.IMREAD_ANYCOLOR)
    
    def get_board_as_CoreImage():
        Core.memoryBuffer.seek(0)
        return CoreImage(io.BytesIO(Core.memoryBuffer.read()), ext='png')

class Application(App):
    gameType = "chess"
    primary_screen = None

    def update_board_corners(x, y, button, pressed):
        if pressed:
            Core.topLeft = (x, y)
        print('{0} at {1}'.format('Pressed' if pressed else 'Released', (x, y)))
        if not pressed:
            Core.botRight = (x,y)
            Core.write_screen_to_buffer()
            return False
    
    def initialize_chess_images_cache(_):
        gameboard.Chess.initialize_chess_images_cache()

    def start_click_and_drag(null): 
        with mouse.Listener(on_click=Application.update_board_corners) as listener:
            listener.join() 

    def build(self):
        self.title = "ChessBotYZ"
        Clock.schedule_interval(Core.board_loop, 0.25)

        layout = BoxLayout()
        layout.orientation = 'vertical'
        layout.add_widget(ToolBar(size_hint=(1, 0.3)))  # Adjusted size_hint
        screen_manager = ScreenManager()
        self.primary_screen = PrimaryScreen(name='primary')
        screen_manager.add_widget(self.primary_screen)  # Added name
        screen_manager.add_widget(SettingsScreen(name='settings'))  # Added name
        screen_manager.current = 'primary' 
        layout.add_widget(screen_manager) 

        return layout
        # Instead use whole screen imshow/cv2 then draw intersecting lines following cursor on that imshow

if __name__ == '__main__':
    Application().run()


