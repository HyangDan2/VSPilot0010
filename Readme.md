# Column Video Mixer: Odd/Even Columns

Column Video Mixer is a desktop PySide6 application that loads two visual sources and mixes them in real time with OpenCV and NumPy. Each source can be a video or a still image.

The current app supports two mix styles:

- Odd/Even Columns: alternates the two sources column by column.
- Checker-board: alternates the two sources in square blocks with a configurable pixel size.

## Features

- Load two independent video or image sources.
- Mix sources in real time through a dedicated mixing thread.
- Switch between odd/even column mixing and checker-board mixing.
- Adjust checker-board block size from the on-screen controls.
- Play, pause, and seek each video source separately.
- Loop video playback when a source reaches the end.
- Feed still images continuously at 30 FPS so they can mix with videos.
- Resize the second source to the first source before mixing when their dimensions differ.
- Display the mixed output with aspect-ratio preserving scaling.
- Toggle source resolution metadata over the video output.
- Swap the two selected sources and restart mixing.
- Toggle fullscreen playback.

## Requirements

Install the Python dependencies listed in [Requirements.txt](Requirements.txt):

```bash
pip install -r Requirements.txt
```

Dependencies:

- PySide6 6.5 or newer
- opencv-python
- numpy

## Usage

Run the application from the project root:

```bash
python main.py
```

Then load two sources and start mixing.

Supported video extensions in the app are `.mp4`, `.avi`, and `.mov`. Other selected files are treated as still images and loaded through OpenCV, so common formats such as JPG and PNG should work when your OpenCV build supports them.

## Controls

Menu actions:

- File > Load 1: choose the first source.
- File > Load 2: choose the second source.
- Play > Start: start or restart decoding and mixing.
- Play > Stop: stop all active decoder and mixer threads.
- Mixing > Odd/Even Columns: use alternating columns.
- Mixing > Checker-board: use checker-board blocks.

Keyboard shortcuts:

- `1`: load source 1.
- `2`: load source 2.
- `Space`: start mixing.
- `P`: stop all playback and mixing.
- `Escape`: toggle fullscreen mode and hide/show the menu bar.
- `Tab`: toggle the resolution metadata overlay.
- `S`: swap source 1 and source 2, then restart mixing.

On-screen overlay:

- Move the mouse near the bottom of the output area to show the control overlay.
- Each source has its own frame slider, frame counter, Play button, and Stop button.
- Use the Mix selector to change the active mixing mode.
- Use Checker pixels to adjust the checker-board block size.

## Project Layout

```text
.
|-- main.py
|-- Requirements.txt
|-- Readme.md
|-- License.txt
`-- Sources/
    |-- ui.py
    |-- decoder.py
    |-- mixer.py
    |-- utils.py
    `-- VideoLabel.py
```

Key modules:

- [main.py](main.py): creates the Qt application and opens `MainWindow`.
- [Sources/ui.py](Sources/ui.py): builds the main window, menus, overlay controls, shortcuts, source loading, thread lifecycle, and still-image feeder.
- [Sources/decoder.py](Sources/decoder.py): decodes video frames on a `QThread`, supports play/pause, seeking, frame counters, and looping.
- [Sources/mixer.py](Sources/mixer.py): consumes frames from both sources, resizes the second source when needed, applies the selected mixing mode, and emits a `QImage` for display.
- [Sources/utils.py](Sources/utils.py): loads still images with OpenCV.
- [Sources/VideoLabel.py](Sources/VideoLabel.py): extends `QLabel` to draw optional resolution metadata over the mixed output.

## License

This project uses the MIT License. See [License.txt](License.txt).
