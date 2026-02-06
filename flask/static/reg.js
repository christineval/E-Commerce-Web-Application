document.addEventListener('DOMContentLoaded', function () {
    const apiBase = 'https://psgc.cloud/api'; // Replace with your API URL

    const regionDropdown = document.getElementById('region');
    const provinceDropdown = document.getElementById('province');
    const cityDropdown = document.getElementById('city');
    const barangayDropdown = document.getElementById('barangay');

    // Populate Regions
    fetch(`${apiBase}/regions`)
        .then(response => response.json())
        .then(data => {
            data.forEach(region => {
                const option = document.createElement('option');
                option.value = region.code;
                option.textContent = region.name;
                regionDropdown.appendChild(option);
            });
        });

    // Handle Region Change
    regionDropdown.addEventListener('change', function () {
        const selectedRegion = regionDropdown.value;
        document.getElementById('region-text').value = regionDropdown.options[regionDropdown.selectedIndex].text;

        // Clear dependent dropdowns
        provinceDropdown.innerHTML = '<option selected disabled>Choose Province</option>';
        cityDropdown.innerHTML = '<option selected disabled>Choose City/Municipality</option>';
        barangayDropdown.innerHTML = '<option selected disabled>Choose Barangay</option>';

        // Fetch provinces for the selected region
        fetch(`${apiBase}/regions/${selectedRegion}/provinces`)
            .then(response => response.json())
            .then(data => {
                data.forEach(province => {
                    const option = document.createElement('option');
                    option.value = province.code;
                    option.textContent = province.name;
                    provinceDropdown.appendChild(option);
                });
            });
    });


    provinceDropdown.addEventListener('change', function () {
        const selectedProvince = provinceDropdown.value;
        document.getElementById('province-text').value = provinceDropdown.options[provinceDropdown.selectedIndex].text;
    
        // Clear dependent dropdowns
        cityDropdown.innerHTML = '<option selected disabled>Choose City/Municipality</option>';
        barangayDropdown.innerHTML = '<option selected disabled>Choose Barangay</option>';
    
        // Fetch cities/municipalities for the selected province
        fetch(`${apiBase}/provinces/${selectedProvince}/cities-municipalities`)
            .then(response => response.json())
            .then(data => {
                if (data.length === 0) {
                    console.error('No cities/municipalities found for this province.');
                    return;
                }
                data.forEach(city => {
                    const option = document.createElement('option');
                    option.value = city.code;
                    option.textContent = city.name; // Use `city.name` to include the name of the city/municipality
                    cityDropdown.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error fetching cities/municipalities:', error);
            });
    });
    

    // Handle City Change
    cityDropdown.addEventListener('change', function () {
        const selectedCity = cityDropdown.value;
        document.getElementById('city-text').value = cityDropdown.options[cityDropdown.selectedIndex].text;

        // Clear dependent dropdown
        barangayDropdown.innerHTML = '<option selected disabled>Choose Barangay</option>';

        // Fetch barangays for the selected city
        fetch(`${apiBase}/cities-municipalities/${selectedCity}/barangays`)
            .then(response => response.json())
            .then(data => {
                data.forEach(barangay => {
                    const option = document.createElement('option');
                    option.value = barangay.code;
                    option.textContent = barangay.name;
                    barangayDropdown.appendChild(option);
                });
            });
    });

    // Handle Barangay Change
    barangayDropdown.addEventListener('change', function () {
        document.getElementById('barangay-text').value = barangayDropdown.options[barangayDropdown.selectedIndex].text;
    });
});




//FOR IMAGE
// Helper function to convert file to Base64
const convertToBase64 = (file) =>
    new Promise((resolve) => {
        const fileReader = new FileReader();
        fileReader.readAsDataURL(file);
        fileReader.onload = () => resolve(fileReader.result);
    });

// Function to handle single image preview
const handleSingleImageUpload = (inputId, previewId) => {
    const inputElement = document.getElementById(inputId);
    const previewContainer = document.getElementById(previewId);

    // Handle file input change event
    inputElement.addEventListener('change', async function () {
        const file = inputElement.files[0];
        if (file && file.type.startsWith('image/')) {
            const imageBase64 = await convertToBase64(file);
            previewContainer.innerHTML = `<img src="${imageBase64}" alt="Image Preview" class="img-preview">`;
        } else {
            previewContainer.innerHTML = `<span class="upload-text">Click or Drag & Drop Image</span>`;
        }
    });

    // Optional: Click the hidden file input when the box is clicked
    previewContainer.parentElement.addEventListener('click', function () {
        inputElement.click();
    });

    // Drag-and-drop image handling
    previewContainer.addEventListener('dragover', function (e) {
        e.preventDefault();
        previewContainer.style.backgroundColor = "#e9e9e9";
    });

    previewContainer.addEventListener('dragleave', function () {
        previewContainer.style.backgroundColor = "#ffffff";
    });

    previewContainer.addEventListener('drop', async function (e) {
        e.preventDefault();
        previewContainer.style.backgroundColor = "#ffffff";

        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            inputElement.files = e.dataTransfer.files; // Set the file input to the dropped file
            const imageBase64 = await convertToBase64(file); // Use Base64 for drag-and-drop preview
            previewContainer.innerHTML = `<img src="${imageBase64}" alt="Image Preview" class="img-preview">`;
        } else {
            previewContainer.innerHTML = `<span class="upload-text">Click or Drag & Drop Image</span>`;
        }
    });
};

// Attach the image preview handler to a single input
handleSingleImageUpload('image-upload', 'image-preview');
