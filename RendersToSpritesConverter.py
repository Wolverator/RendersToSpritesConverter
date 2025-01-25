import json
import os.path
import time
from threading import Thread
from traceback import format_exception
from PIL import Image, ImageChops, ImageFilter
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QVBoxLayout, QWidget,\
    QFileDialog, QHBoxLayout, QTextEdit, QProgressBar, QCheckBox

# sprites-making tool by ShereKhanRomeo
# this code is free to use, change and post anywhere as I don't care XD

# saves masks as a separate file alongside processed pics
# red color shows which pixels will be saved from original pic and other pixels will be transparent
# left here to let you experiment with settings and see what suits better for your needs
SAVE_MASKS_PREVIEW = False
CONVERTER_SETTINGS_PATH = "ConverterSettings.json"
OUTPUT_PLACEHOLDER = "select output folder"
TITLE = "Sprites-making tool by ShereKhanRomeo"
THREADS = []

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
        self.setFixedSize(QSize(720, 300))
        self.setWindowTitle(TITLE)
        self.done = 0
        self.picsToDo = 0
        self.startedConverting = None
        self.ignoredPics = []

        self.settings = self.tryLoadSettings()
        if 'webpMethod' not in self.settings.keys():
            self.settings['webpMethod'] = 6
        if 'webpLossless' not in self.settings.keys():
            self.settings['webpLossless'] = True
        if 'webpQuality' not in self.settings.keys():
            self.settings['webpQuality'] = 0
        if 'pngCompression' not in self.settings.keys():
            self.settings['pngCompression'] = 0
        if 'pngOptimize' not in self.settings.keys():
            self.settings['pngOptimize'] = True

        self.labelBgImage = QLabel(text="Drop background image:")
        self.labelBgImageHere = MyLineEdit()
        self.labelBgImageHere.setText("Here")

        self.labelSpriteImages = QLabel(text="Drop sprites images:")
        self.labelSpriteImagesHere = MyTextEdit()
        self.labelSpriteImagesHere.setText("Here")

        self.labelSettings = QLabel(text="============================= Settings (hover over setting name for hints) "
                                         "=============================")

        self.outputDirLabel = QLabel(text="Output folder:")
        self.outputDirPath = QLineEdit()
        self.outputDirPath.setText(str(self.settings['output']))
        self.outputDirButton = QPushButton("Select")
        self.outputDirButton.clicked.connect(self.outputDirSelected)

        self.sharpnessLabel = QLabel(text="Sharpness:")
        self.sharpnessLabel.setToolTip("How sharp sprites contours are meant to be (decimal from 0 to 7):\n"
                                       "0 - is 'turned off', sprites will contain lot of noise, but result in more "
                                       "smoothness\n "
                                       "1.5 - recommended\n"
                                       "7 - sharp, less noise, sprites are like cut out from paper with scissors")
        self.sharpnessInput = QLineEdit()
        self.sharpnessInput.setText(str(self.settings['sharpness']))
        self.noiseLabel = QLabel(text="Noise threshold:")
        self.noiseLabel.setToolTip("Cleanses too small differences (decimal from 0 to 10):\n"
                                   "0 - cleans nothing\n"
                                   "2.5 - recommended\n"
                                   "10 and higher are not recommended")
        self.noiseInput = QLineEdit()
        self.noiseInput.setText(str(self.settings['noise']))
        self.multithreadingLabel = QLabel(text="Multithreading:")
        self.multithreadingLabel.setToolTip("If checked all sprite pics will be processed simultaneously.\nOtherwise "
                                            "one-by-one with less RAM usage.")
        self.multithreadingCheckBox = QCheckBox()
        self.multithreadingCheckBox.setChecked(self.settings['multi'])

        self.pngOptimizeLabel = QLabel(text="Optimize (for PNG):")
        self.pngOptimizeLabel.setToolTip("If present and true, instructs the PNG writer to make the output file as "
                                         "small as possible.\n "
                                         "This includes extra processing in order to find optimal encoder settings.")
        self.pngOptimizeCheckBox = QCheckBox()
        self.pngOptimizeCheckBox.setChecked(self.settings['pngOptimize'])

        self.webpMethodLabel = QLabel(text="Method (for WEBP):")
        self.webpMethodLabel.setToolTip("Quality/speed trade-off (whole number from 0 to 6):\n"
                                        "0 - faster but worse quality\n"
                                        "6 - slower but better quality")
        self.webpMethodInput = QLineEdit()
        self.webpMethodInput.setFixedWidth(30)
        self.webpMethodInput.setText(str(self.settings['webpMethod']))

        self.webpLosslessLabel = QLabel(text="Lossless (for WEBP):")
        self.webpLosslessLabel.setToolTip("If checked changes to lossless compression and 'Quality' becomes "
                                          "'Compression'.")
        self.webpLosslessCheckBox = QCheckBox()

        self.webpQualityLabel = QLabel(text="Quality (for WEBP):")
        self.webpQualityLabel.setToolTip("Integer, 0-100, Defaults to 80. For lossy, 0 gives the smallest file size "
                                         "and 100 the largest.\n "
                                         "For lossless, this parameter is the amount of effort put into the "
                                         "compression:\n "
                                         "0 is the fastest, but gives larger files compared to the slowest, but best, "
                                         "100.")
        self.webpLosslessCheckBox.stateChanged.connect(self.losslessCheckboxChecked)
        self.webpLosslessCheckBox.setChecked(self.settings['webpLossless'])
        self.webpQualityInput = QLineEdit()
        self.webpQualityInput.setFixedWidth(30)
        self.webpQualityInput.setText(str(self.settings['webpQuality']))

        self.pngCompressionLabel = QLabel(text="Compression (for PNG):")
        self.pngCompressionLabel.setToolTip("How compressed resulting PNGs are meant to be (whole number from 0 to "
                                            "9).\n "
                                            "0 - no compression\n"
                                            "1 - fastest compression\n"
                                            "9 - best compression")
        self.pngCompressionInput = QLineEdit()
        self.pngCompressionInput.setFixedWidth(30)
        self.pngCompressionInput.setText(str(self.settings['pngCompression']))

        self.settingsWillBeSavedLabel = QLabel(text="Your settings will be remembered in 'ConverterSettings.json'.")
        self.startConvertingButton = QPushButton("Convert!")
        self.startConvertingButton.clicked.connect(self.startConverting)

        self.picsSizeBeforeLabel = QLabel()
        self.picsSizeBeforeLabel.setFixedWidth(80)
        self.picsDoneLabel = QLabel("0/0")
        self.picsDoneLabel.setFixedWidth(30)
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1)
        self.progressBar.setValue(0)
        self.picsSizeAfterLabel = QLabel()
        self.picsSizeAfterLabel.setFixedWidth(75)

        layoutMain = QVBoxLayout()
        layoutBG = QHBoxLayout()
        layoutBG.addWidget(self.labelBgImage)
        layoutBG.addWidget(self.labelBgImageHere)
        layoutSprites = QVBoxLayout()
        layoutSprites.addWidget(self.labelSpriteImages)
        layoutSprites.addWidget(self.labelSpriteImagesHere)
        layoutSettingsTitle = QVBoxLayout()
        layoutSettingsTitle.addWidget(self.labelSettings)
        layoutOutputDir = QHBoxLayout()
        layoutOutputDir.addWidget(self.outputDirLabel)
        layoutOutputDir.addWidget(self.outputDirPath)
        layoutOutputDir.addWidget(self.outputDirButton)
        layoutSettings = QHBoxLayout()
        layoutSettings.addWidget(self.sharpnessLabel)
        layoutSettings.addWidget(self.sharpnessInput)
        layoutSettings.addWidget(self.noiseLabel)
        layoutSettings.addWidget(self.noiseInput)
        layoutSettings.addWidget(self.multithreadingLabel)
        layoutSettings.addWidget(self.multithreadingCheckBox)
        layoutSettings.addWidget(self.pngOptimizeLabel)
        layoutSettings.addWidget(self.pngOptimizeCheckBox)
        layoutSettings2 = QHBoxLayout()
        layoutSettings2.addWidget(self.webpMethodLabel)
        layoutSettings2.addWidget(self.webpMethodInput)
        layoutSettings2.addWidget(self.webpLosslessLabel)
        layoutSettings2.addWidget(self.webpLosslessCheckBox)
        layoutSettings2.addWidget(self.webpQualityLabel)
        layoutSettings2.addWidget(self.webpQualityInput)
        layoutSettings2.addWidget(self.pngCompressionLabel)
        layoutSettings2.addWidget(self.pngCompressionInput)
        layoutOther = QHBoxLayout()
        layoutOther.addWidget(self.settingsWillBeSavedLabel)
        layoutOther.addWidget(self.startConvertingButton)
        layoutInfo = QHBoxLayout()
        layoutInfo.addWidget(self.picsSizeBeforeLabel)
        layoutInfo.addWidget(self.picsDoneLabel)
        layoutInfo.addWidget(self.progressBar)
        layoutInfo.addWidget(self.picsSizeAfterLabel)

        layoutMain.addLayout(layoutBG)
        layoutMain.addLayout(layoutSprites)
        layoutMain.addLayout(layoutSettingsTitle)
        layoutMain.addLayout(layoutOutputDir)
        layoutMain.addLayout(layoutSettings)
        layoutMain.addLayout(layoutSettings2)
        layoutMain.addLayout(layoutOther)
        layoutMain.addLayout(layoutInfo)

        container = QWidget()
        container.setLayout(layoutMain)
        # Set main widget Window.
        self.setCentralWidget(container)

    def outputDirSelected(self):
        self.outputDirPath.setText(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.trySaveSettings()

    def losslessCheckboxChecked(self):
        if self.webpLosslessCheckBox.isChecked():
            self.webpQualityLabel.setText("Compression (for WEBP):")
        else:
            self.webpQualityLabel.setText("Quality (for WEBP):")

    def tryLoadSettings(self):
        if os.path.exists(CONVERTER_SETTINGS_PATH):
            with open(CONVERTER_SETTINGS_PATH) as settingsFile:
                return json.load(settingsFile)
        else:
            return {
                'output': OUTPUT_PLACEHOLDER,
                'sharpness': 2.9,
                'noise': 2.9,
                'multi': False,
                'pngCompression': 0,
                'pngOptimize': True,
                'webpMethod': 6,
                'webpLossless': True,
                'webpQuality': 100
            }

    def trySaveSettings(self):
        if not self.outputDirPath.text() == OUTPUT_PLACEHOLDER:
            self.settings['output'] = self.outputDirPath.text()
            self.settings['sharpness'] = self.sharpnessInput.text()
            self.settings['noise'] = self.noiseInput.text()
            self.settings['multi'] = self.multithreadingCheckBox.isChecked()
            self.settings['pngCompression'] = self.pngCompressionInput.text()
            self.settings['pngOptimize'] = self.pngOptimizeCheckBox.isChecked()
            self.settings['webpMethod'] = self.webpMethodInput.text()
            self.settings['webpLossless'] = self.webpLosslessCheckBox.isChecked()
            self.settings['webpQuality'] = self.webpQualityInput.text()
            with open(CONVERTER_SETTINGS_PATH, "w") as settingsFile:
                json.dump(self.settings, settingsFile)
                settingsFile.close()

    def calculateSizeBefore(self):
        size = 0
        for sprite in self.labelSpriteImagesHere.toPlainText().splitlines():
            if sprite != '' and sprite not in self.ignoredPics and sprite != self.labelBgImageHere.text():
                size += os.path.getsize(sprite)
        return str(round(size / 1024))

    def calculateSizeAfter(self):
        size = 0
        for sprite in self.labelSpriteImagesHere.toPlainText().splitlines():
            if sprite != '' and sprite not in self.ignoredPics and sprite != self.labelBgImageHere.text():
                size += os.path.getsize(self.outputDirPath.text() + sprite[sprite.rfind('/'):])
        return str(round(size / 1024))

    def startConverting(self):
        global THREADS
        self.trySaveSettings()
        if not os.path.exists(self.labelBgImageHere.text()):
            print("Nope! Can't find background picture path.")
        elif not os.path.isfile(self.labelBgImageHere.text()):
            print("Nope! Background picture path is not a file.")
        elif self.labelSpriteImagesHere != "Here": 
            sprites = self.labelSpriteImagesHere.toPlainText().splitlines()
            self.picsToDo = len(sprites)
            self.done = 0
            self.progressBar.setMaximum(self.picsToDo * 6)
            self.progressBar.setValue(0)
            self.picsDoneLabel.setText(str(self.done) + "/" + str(self.picsToDo))
            self.picsSizeBeforeLabel.setText("Before: ... KB")
            self.picsSizeAfterLabel.setText("After: ... KB")
            self.setWindowTitle(TITLE)
            self.ignoredPics = []
            self.startedConverting = time.time()
            for sprite in sprites:
                if sprite != self.labelBgImageHere.text():
                    thread = Thread(target=self.processPicsWithNoiseThreshold,
                                    args=(self.labelBgImageHere.text(), sprite, self.outputDirPath.text() + '/', float(self.sharpnessInput.text()), float(self.noiseInput.text())))
                    thread.daemon = True
                    thread.start()
                    THREADS.append(thread)
                    if not self.multithreadingCheckBox.isChecked():
                        thread.join()
                else:
                    self.picsToDo -= 1
                    self.progressBar.setMaximum(self.picsToDo * 6)

            if not self.multithreadingCheckBox.isChecked():
                self.setWindowTitle(TITLE + " - Done in " + str(round(time.time() - self.startedConverting, 2)) + " seconds")

    def processPicsWithNoiseThreshold(self, _bgPic, _spritePic, _save_to, _sharpness_lvl, _noise_threshold):
        self.startConvertingButton.setText("Processing...")
        if not self.multithreadingCheckBox.isChecked():
            before = self.progressBar.value()
        try:
            bg = Image.open(_bgPic)
            self.progressBar.setValue(self.progressBar.value() + 1)
            sprite = Image.open(_spritePic)
            self.progressBar.setValue(self.progressBar.value() + 1)
            diff1 = ImageChops.difference(bg, sprite).convert('RGBA').filter(ImageFilter.GaussianBlur(_sharpness_lvl))
            self.progressBar.setValue(self.progressBar.value() + 1)
            newimdata = []
            dat = diff1.getdata()
            for color in dat:
                if sum(color[:3]) <= _noise_threshold:
                    newimdata.append((0, 0, 0, 0))
                else:
                    newimdata.append((255, 0, 0, 255))
            self.progressBar.setValue(self.progressBar.value() + 1)
            mask = Image.new('RGBA', diff1.size)
            # noinspection PyTypeChecker
            mask.putdata(newimdata)
            picName = _spritePic[_spritePic.rfind('/') + 1:]
            self.progressBar.setValue(self.progressBar.value() + 1)
            if SAVE_MASKS_PREVIEW:
                mask.save(_save_to + 'diff' + picName)
            ImageChops.composite(sprite, Image.new("RGBA", sprite.size, 0), mask) \
                .save(
                (_save_to + picName),
                optimize=bool(self.pngOptimizeCheckBox),
                compress_level=int(self.pngCompressionInput.text()),
                losseless=self.webpLosslessCheckBox.isChecked(),
                method=int(self.webpMethodInput.text()),
                quality=int(self.webpQualityInput.text())
            )

            self.progressBar.setValue(self.progressBar.value() + 1)
            self.done += 1
            self.picsDoneLabel.setText(str(self.done) + "/" + str(self.picsToDo))
        except ValueError:
            print("Failed to process sprite " + _spritePic[_spritePic.rfind('/') + 1:] + " with background " + _bgPic[_bgPic.rfind('/') + 1:] +
                  " Try setting another background for this sprite.")
            self.ignoredPics.append(_spritePic)
            self.picsToDo -= 1
            self.progressBar.setMaximum(self.picsToDo * 6)
        except Exception as picProcessingError:
            print("ERROR - " + str("".join(format_exception(type(picProcessingError), value=picProcessingError, tb=picProcessingError.__traceback__))).split(
                "The above exception was the direct cause of the following")[0])
            print("Failed to process sprite " + _spritePic[_spritePic.rfind('/') + 1:] + " with background " + _bgPic[_bgPic.rfind('/') + 1:])
            self.ignoredPics.append(_spritePic)
            self.picsToDo -= 1
            self.progressBar.setMaximum(self.picsToDo * 6)
        finally:
            if self.picsDoneLabel.text() == str(self.picsToDo) + "/" + str(self.picsToDo):
                self.startConvertingButton.setText("Convert!")
                self.picsSizeBeforeLabel.setText("Before: " + self.calculateSizeBefore() + " KB")
                self.picsSizeAfterLabel.setText("After: " + self.calculateSizeAfter() + " KB")


if __name__ == "__main__":
    try:
        window = MainWindow()  # window starts hidden
        window.show()  # need to show it manually
        # Run the loop
        app.exec()
    except Exception as error:
        print("ERROR - " + str("".join(format_exception(type(error), value=error, tb=error.__traceback__))).split(
            "The above exception was the direct cause of the following")[0])
    finally:
        for t in THREADS:
            t.join()
