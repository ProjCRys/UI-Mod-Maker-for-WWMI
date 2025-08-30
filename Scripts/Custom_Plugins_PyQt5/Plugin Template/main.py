import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PyQt5.QtGui import QPixmap

class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Image Display App')
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel('This is the main GUI2')
        self.layout.addWidget(self.label)

        self.image_label = QLabel()  # Label to display images
        self.layout.addWidget(self.image_label)

        self.button = QPushButton('Show Image')
        self.button.clicked.connect(self.show_image)
        self.layout.addWidget(self.button)

    def show_image(self):
        # Open a file dialog to select an image
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)", options=options)
        if file_name:
            pixmap = QPixmap(file_name)
            self.image_label.setPixmap(pixmap)
            self.image_label.setScaledContents(True)  # Adjust image to label size

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Main()
    ex.show()
    sys.exit(app.exec_())
