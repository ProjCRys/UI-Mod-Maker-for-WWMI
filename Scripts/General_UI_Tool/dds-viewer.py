import os
import imageio
from tkinter import Tk, Label, Button, filedialog, Frame
from PIL import Image, ImageTk

class DDSViewer:
    def __init__(self, master):
        self.master = master
        self.master.title("DDS Image Viewer")
        
        self.frame = Frame(self.master)
        self.frame.pack()

        self.label = Label(self.frame)
        self.label.pack()

        self.btn_open = Button(self.frame, text="Open DDS File", command=self.open_file)
        self.btn_open.pack()

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("DDS files", "*.dds")])
        if file_path:
            self.show_image(file_path)

    def show_image(self, file_path):
        # Use imageio to read the DDS image
        try:
            image = imageio.imread(file_path)
            image_pil = Image.fromarray(image)

            # Resize image for better display
            image_pil.thumbnail((800, 600))

            # Convert to ImageTk format for displaying in Tkinter
            self.img_tk = ImageTk.PhotoImage(image_pil)

            # Update label with the new image
            self.label.config(image=self.img_tk)
            self.label.image = self.img_tk  # Keep a reference to avoid garbage collection
        except Exception as e:
            print(f"Error reading the image: {e}")

if __name__ == "__main__":
    root = Tk()
    viewer = DDSViewer(root)
    root.mainloop()
