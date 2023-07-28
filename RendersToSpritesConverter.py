import json
import os.path
from threading import Thread

from PIL import Image, ImageChops, ImageFilter
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QVBoxLayout, QWidget, QFileDialog, QHBoxLayout, QTextEdit, QProgressBar

# sprites-making tool by ShereKhanRomeo
# this code is free to use, change and post anywhere as I don't care XD

# saves masks as a separate file alongside processed pics
# red color shows which pixels will be saved from original pic and other pixels will be transparent
# left here to let you experiment with settings and see what suits better for your needs
_save_masks_preview = False

_converter_settings_path = "ConverterSettings.json"
_output_placeholder = "select output folder"


def processPicsWithNoiseThreshold(_bgPic, _spritePic, _save_to, _sharpness_lvl, _noise_threshold):
    bg = Image.open(_bgPic)
    sprite = Image.open(_spritePic)
    diff1 = ImageChops.difference(bg, sprite).convert('RGBA').filter(ImageFilter.GaussianBlur(_sharpness_lvl))
    newimdata = []
    dat = diff1.getdata()
    for color in dat:
        if color[0] + color[1] + color[2] <= _noise_threshold:
            newimdata.append((0, 0, 0, 0))
        else:
            newimdata.append((255, 0, 0, 255))
    mask = Image.new('RGBA', diff1.size)
    mask.putdata(newimdata)
    picName = _spritePic[_spritePic.rfind('/') + 1:]
    if _save_masks_preview:
        mask.save(_save_to + 'diff' + picName)
    ImageChops.composite(sprite, Image.new("RGBA", sprite.size, 0), mask) \
        .save((_save_to + picName), compress_level=6, lossless=True, quality=50, method=6)
    # regarding save options:

    # Only matters when saving in PNG:
    # compress_level (default is 6, 0 - no compression, 1 is fastest and 9 is best compression

    # Only matters when saving in WEBP:
    # lossless (if True, switches to lossless compression and makes "quality" param be 0-no compression, 100- max compression)
    # quality (if lossless is False, 0 gives the smallest size and 100 the largest)
    # method (quality/speed trade-off (0=fast, 6=slower but better), defaults to 4)


app = QApplication([])


class MyLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        self.setText(e.mimeData().urls()[0].toString().strip("file:///"))


class MyTextEdit(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        self.setText(e.mimeData().urls()[0].toString().strip("file:///"))
        if len(e.mimeData().urls()) > 1:
            for line in e.mimeData().urls()[1:]:
                self.append(line.toString().strip("file:///"))


# QMainWindow to settle main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(QSize(600, 300))
        self.setWindowTitle("Sprites-making tool by ShereKhanRomeo")

        self.settings = self.tryLoadSettings()

        self.labelBgImage = QLabel(text="Drop background image:")
        self.labelBgImageHere = MyLineEdit()
        self.labelBgImageHere.setText("Here")

        self.labelSpriteImages = QLabel(text="Drop sprites images:")
        self.labelSpriteImagesHere = MyTextEdit()
        self.labelSpriteImagesHere.setText("Here")

        self.outputDirLabel = QLabel(text="Output folder:")
        self.outputDirPath = QLineEdit()
        self.outputDirPath.setText(str(self.settings['output']))
        self.outputDirButton = QPushButton("Select")
        self.outputDirButton.clicked.connect(self.outputDirSelected)

        self.sharpnessLabel = QLabel(text="Sharpness (hover for help):")
        self.sharpnessLabel.setToolTip("""How sharp sprites contours are meant to be.
0 - is "turned off", sprites will contain lot of noise, but result in more smoothness
1.5 - recommended
7 - sharp, less noise, sprites are like cut out from paper with scissors""")
        self.sharpnessInput = QLineEdit()
        self.sharpnessInput.setText(str(self.settings['sharpness']))
        self.noiseLabel = QLabel(text="Noise threshold (hover for help):")
        self.noiseLabel.setToolTip("""Cleanses too small differences
0 - cleans nothing
1.5 - recommended
10 and higher are not recommended""")
        self.noiseInput = QLineEdit()
        self.noiseInput.setText(str(self.settings['noise']))

        self.settingsLabel = QLabel(text="Your selected output path, sharpness and noise settings will be remembered in 'ConverterSettings.json'.")
        self.startConvertingButton = QPushButton("Convert!")
        self.startConvertingButton.clicked.connect(self.startConverting)

        self.infoLabel = QLabel()
        self.infoLabel.setFixedWidth(50)
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1)
        self.progressBar.setValue(0)

        layoutMain = QVBoxLayout()
        layoutBG = QHBoxLayout()
        layoutBG.addWidget(self.labelBgImage)
        layoutBG.addWidget(self.labelBgImageHere)
        layoutSprites = QVBoxLayout()
        layoutSprites.addWidget(self.labelSpriteImages)
        layoutSprites.addWidget(self.labelSpriteImagesHere)
        layoutOutputDir = QHBoxLayout()
        layoutOutputDir.addWidget(self.outputDirLabel)
        layoutOutputDir.addWidget(self.outputDirPath)
        layoutOutputDir.addWidget(self.outputDirButton)
        layoutSettings = QHBoxLayout()
        layoutSettings.addWidget(self.sharpnessLabel)
        layoutSettings.addWidget(self.sharpnessInput)
        layoutSettings.addWidget(self.noiseLabel)
        layoutSettings.addWidget(self.noiseInput)
        layoutOther = QVBoxLayout()
        layoutOther.addWidget(self.settingsLabel)
        layoutOther.addWidget(self.startConvertingButton)
        layoutInfo = QHBoxLayout()
        layoutInfo.addWidget(self.infoLabel)
        layoutInfo.addWidget(self.progressBar)

        layoutMain.addLayout(layoutBG)
        layoutMain.addLayout(layoutSprites)
        layoutMain.addLayout(layoutOutputDir)
        layoutMain.addLayout(layoutSettings)
        layoutMain.addLayout(layoutOther)
        layoutMain.addLayout(layoutInfo)

        container = QWidget()
        container.setLayout(layoutMain)
        # Set main widget Window.
        self.setCentralWidget(container)

    def outputDirSelected(self):
        self.outputDirPath.setText(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.trySaveSettings()

    def tryLoadSettings(self):
        if os.path.exists(_converter_settings_path):
            with open(_converter_settings_path) as settingsFile:
                return json.load(settingsFile)
        else:
            return {
                'sharpness': 2.9,
                'noise': 2.9,
                'output': _output_placeholder
            }

    def trySaveSettings(self):
        if not self.outputDirPath.text() == _output_placeholder:
            self.settings['output'] = self.outputDirPath.text()
            self.settings['sharpness'] = self.sharpnessInput.text()
            self.settings['noise'] = self.noiseInput.text()
            with open(_converter_settings_path, "w") as settingsFile:
                json.dump(self.settings, settingsFile)
                settingsFile.close()

    def startConverting(self):
        self.trySaveSettings()
        sprites = self.labelSpriteImagesHere.toPlainText().splitlines()
        picsToDo = len(sprites)
        done = 0
        self.progressBar.setMaximum(picsToDo)
        self.infoLabel.setText(str(done) + "/" + str(picsToDo))
        for sprite in sprites:
            thread = Thread(target=processPicsWithNoiseThreshold,
                            args=(self.labelBgImageHere.text(), sprite, self.outputDirPath.text() + '/', float(self.sharpnessInput.text()), float(self.noiseInput.text())))
            thread.daemon = True
            # processPicsWithNoiseThreshold(self.labelBgImageHere.text(), sprite, self.outputDirPath.text()+'/', float(self.sharpnessInput.text()), float(self.noiseInput.text()))
            thread.start()
            #thread.join()
            done += 1
            self.infoLabel.setText(str(done) + "/" + str(picsToDo))
            self.progressBar.setValue(done)


window = MainWindow()  # window starts hidden
window.show()  # need to show it manually

# Run the loop
app.exec()
