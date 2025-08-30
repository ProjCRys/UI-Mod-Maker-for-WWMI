@echo off
python -m venv venv
call venv\Scripts\activate
pip install PyQt5 opencv-python numpy Pillow PyQtWebEngine imageio ollama imageio[pyav] imageio[ffmpeg]
echo Setup completed successfully!
pause