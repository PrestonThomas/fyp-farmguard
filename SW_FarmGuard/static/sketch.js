let socket;
let temperatures = [];
let tempSlider;

function setup() {
  createCanvas(320, 240);
  pixelDensity(1);
  noLoop();
  background('black');

  socket = io.connect();
  socket.on('temperature', data => {
    console.log('Received data type:', typeof data);
    const temperaturesArray = Object.values(data);

    temperatures = temperaturesArray;
    redraw();
  });
  tempSlider = createSlider(20, 100, 60);
  let canvasPosition = getCanvasPosition();
  tempSlider.position(10, canvasPosition.y + height + 10);
  tempSlider.input(() => redraw());
}

function getCanvasPosition() {
  let canvas = document.querySelector('canvas');
  let rect = canvas.getBoundingClientRect();
  return {
    x: rect.left,
    y: rect.top
  };
}

function temperatureToColor(temperature) {
  // Define the Ironbow color map
  let colors = [
    color(0, 0, 0),
    color(6, 0, 18),
    color(32, 0, 39),
    color(61, 0, 61),
    color(88, 3, 78),
    color(112, 12, 93),
    color(134, 26, 104),
    color(157, 43, 114),
    color(178, 63, 123),
    color(201, 86, 131),
    color(221, 111, 138),
    color(240, 137, 145),
    color(255, 166, 152),
    color(255, 195, 161),
    color(255, 225, 169),
    color(255, 255, 178),
    color(255, 255, 201),
    color(255, 255, 227),
    color(255, 255, 255)
  ];

  let sliderValue = tempSlider.value();
  
  let index = int(map(temperature, sliderValue - 20, sliderValue + 20, 0, colors.length - 1));
  index = constrain(index, 0, colors.length - 1);

  return colors[index];
}


function draw() {
  background(0); 
  console.log('Drawing temperatures:', temperatures);
  const cellWidth = width / 32;
  const cellHeight = height / 24;
  for (let row = 0; row < temperatures.length; row++) {
    const temperatureRow = temperatures[row];
    for (let column = 0; column < temperatureRow.length; column++) {
      const temperature = temperatureRow[column];
      if (temperature) {
        const x = column * cellWidth;
        const y = row * cellHeight;
        const clr = temperatureToColor(temperature);
        fill(clr);
        rect(x, y, cellWidth, cellHeight);
      }
    }
  }
}
