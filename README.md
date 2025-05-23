# Michelin-Plotter

Michelin-Plotter is a cross-platform graphical application (Windows) designed for real-time visualization of serial port (UART) data. It is particularly useful for applications in electronics, embedded systems, and sensor monitoring.

## Main Features

* **Real-time Visualization:** Immediate plotting of data received through serial ports.
* **Multiple Channels:** Supports up to 4 simultaneous channels.
* **Customizable Interface:**

  * Editable labels for plots and axes.
  * Flexible channel-to-plot assignment.
  * Individual color selection for each channel.
  * Control over the maximum number of displayed samples.
* **Easy Serial Connection:** Simple setup of port and baudrate from the interface.

## Requirements

* Python 3.x
* PyQt5
* PySerial
* PyQtGraph

## Installation (from source)

1. Clone the repository:

```bash
git clone https://github.com/Michel1297/Michelin-Plotter.git
```

2. Install dependencies:

```bash
pip install pyqt5 pyserial pyqtgraph
```

3. Run the application:

```bash
python MICHELIN-PLOTTER.py
```

## Usage

* Connect your device via serial port (UART).
* Open Michelin-Plotter.
* Select the port and baudrate in the sidebar.
* Click the **"Connect"** button.
* Configure each channel and plot according to your needs.

**Expected data format:**

```
value1,value2,value3,value4
```

Example:

```
1.23,3.45,2.34,4.56
```

## Executable Download (Windows)

Download the executable version for Windows from [Releases](https://github.com/yourusername/Michelin-Plotter/releases).

## License

This project is licensed under the **MIT** license. See the `LICENSE` file for more details.
