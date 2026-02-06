const  sideMenu = document.querySelector('aside');
const menuBtn = document.querySelector('#menu_bar');
const closeBtn = document.querySelector('#close_btn');


// dashboard

menuBtn.addEventListener('click',()=>{
       sideMenu.style.display = "block"
})
closeBtn.addEventListener('click',()=>{
    sideMenu.style.display = "none"
})

themeToggler.addEventListener('click',()=>{
     document.body.classList.toggle('dark-theme-variables')
     themeToggler.querySelector('span:nth-child(1').classList.toggle('active')
     themeToggler.querySelector('span:nth-child(2').classList.toggle('active')
})

// feedback

document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;

    document.querySelectorAll('.sidebar a').forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.endsWith(href)) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
});

// reports

document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;

    document.querySelectorAll('.sidebar a').forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.endsWith(href)) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
});

// settings

document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;

    document.querySelectorAll('.sidebar a').forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.endsWith(href)) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
});


// registration 
addressdocument.addEventListener('DOMContentLoaded', function () {
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