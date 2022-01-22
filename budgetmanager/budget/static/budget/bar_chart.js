//Yearly Chart:
const first = document.getElementById('barChart').getContext('2d');
const months = ['January', 'Febuary', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

var income = document.getElementById('income').innerHTML.split(",");
var expenses = document.getElementById('expenses').innerHTML.split(",");

var incomeBorderColours = [];

//Change border of income when expenses are higher than income
//Problem: Legend always gets the first element, so in January the legend could have a red border
for(var i = 0; i < 12; i++) {
    if(expenses[i] > income[i]) {
        incomeBorderColours.push('rgba(255, 0, 0, 1)');
    }
    else {
        incomeBorderColours.push('rgba(255, 0, 0, 0)');
    }
}

var barData = {
    labels: months,
    datasets: [
        {
            label: 'Income',
            data: income,
            backgroundColor: [
                'rgba(0, 255, 0, 0.7)'
            ],
            borderColor: incomeBorderColours,
            borderWidth: 3,
        },
        {
            label: 'Expenses',
            data: expenses,
            backgroundColor: [
                'rgba(0, 0, 255, 0.7)'
            ],
            borderColor: 'rgba(0, 0, 255, 0)',
            borderWidth: 3
        }
    ]
};

const monthlyChart = new Chart(first, {
    type: 'bar',
    data: barData,
    options: {
        plugins: {
            title: {
                text: 'This year\'s balance',
                display: true,
                font: {
                    size: 16
                }
            }
        }
    }
});