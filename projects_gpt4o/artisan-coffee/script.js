document.addEventListener('DOMContentLoaded', function() {
    // Dark Mode Toggle
    const currentMode = localStorage.getItem('dark-mode') || 'disabled';
    if (currentMode === 'enabled') {
        body.classList.add('dark-mode');
    }
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const body = document.body;

    // Load dark mode preference from localStorage
    if (localStorage.getItem('dark-mode') === 'enabled') {
        body.classList.add('dark-mode');
    }

    darkModeToggle.addEventListener('click', function() {
        body.classList.toggle('dark-mode');
        if (body.classList.contains('dark-mode')) {
            localStorage.setItem('dark-mode', 'enabled');
        } else {
            localStorage.setItem('dark-mode', 'disabled');
        }
    });

    // Subscription Toggle
    const monthlyButton = document.getElementById('monthly');
    const annualButton = document.getElementById('annual');
    const prices = document.querySelectorAll('tbody td:nth-child(2)');

    monthlyButton.addEventListener('click', function() {
        prices.forEach(price => {
            price.textContent = `$${(parseInt(price.textContent.slice(1)) / 12).toFixed(2)}`;
        });
    });

    annualButton.addEventListener('click', function() {
        prices.forEach(price => {
            price.textContent = `$${(parseInt(price.textContent.slice(1)) * 12).toFixed(2)}`;
        });
    });

    // Brew Guide Tabs
    tabcontent.forEach(content => content.style.display = 'none');
    tabcontent[0].style.display = 'block';
    const tablinks = document.querySelectorAll('.tablinks');
    const tabcontent = document.querySelectorAll('.tabcontent');

    tablinks.forEach((tab, index) => {
        tab.addEventListener('click', function() {
            tabcontent.forEach(content => content.style.display = 'none');
            tabcontent[index].style.display = 'block';
        });
    });

    // FAQ Accordion
    const accordionButtons = document.querySelectorAll('.accordion-button');

    accordionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const content = this.nextElementSibling;
            content.style.display = content.style.display === 'block' ? 'none' : 'block';
        });
    });
});