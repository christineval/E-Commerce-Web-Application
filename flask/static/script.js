//quantity selector
function increase() {
    let quantity = document.getElementById("quantity");
    let currentValue = parseInt(quantity.value);
    if (currentValue < 99) {
      quantity.value = currentValue + 1;
    }
  }
  
  function decrease() {
    let quantity = document.getElementById("quantity");
    let currentValue = parseInt(quantity.value);
    if (currentValue > 1) {
      quantity.value = currentValue - 1;
    }
  }
  