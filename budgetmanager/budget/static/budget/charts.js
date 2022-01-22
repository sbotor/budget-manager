function createPieChart() {
    const pieIncome = document.getElementById('pieIncome').getContext('2d');
    const pieExpenses = document.getElementById('pieExpenses').getContext('2d');

    let incomeData = {};
    let expensesData = {};

    const opData = JSON.parse(document.getElementById('operationData').innerHTML);
    opData.forEach(element => {
        const op = JSON.parse(element);

        const opAmount = parseFloat(op.amount);
        const labelInfo = op.label

        if (opAmount > 0) {
            addPieData(incomeData, labelInfo, opAmount);
        } else {
            addPieData(expensesData, labelInfo, opAmount);
        }
    });

    renderPieChart(pieIncome, incomeData, "This month's income");
    renderPieChart(pieExpenses, expensesData, "This month's expenses");
}

function addPieData(data, labelInfo, amount) {
    const labelId = labelInfo[0];
    const labelName = labelInfo[1];

    if (data.hasOwnProperty(labelId)) {
        data[labelId].amount += Math.abs(amount);
    } else {
        data[labelId] = {
            amount: Math.abs(amount),
            label: labelName
        };
    }
}

function renderPieChart(target, chartData, title) {
    let labels = []
    let amounts = []
    for (const labelId in chartData) {
        currentLabel = chartData[labelId]

        labels.push(currentLabel.label);
        amounts.push(currentLabel.amount);
    }

    const data = {
        labels: labels,
        datasets: [
            {
                data: amounts,
                backgroundColor: colours
            }
        ]
    };

    new Chart(target, {
        type: "pie",
        data: data,
        options: {
            plugins: {
                title: {
                    text: title + currency,
                    display: true,
                    font: {
                        size: 16
                    }
                }
            }
        }
    })
}

function createBarChart() {
    //Yearly Chart:
    const barChart = document.getElementById('barChart').getContext('2d');

    const incomeByMonth = document.getElementById('income').innerHTML.split(",");
    const expensesByMonth = document.getElementById('expenses').innerHTML.split(",");

    //Change border of income when expenses are higher than income
    //Problem: Legend always gets the first element, so in January the legend could have a red border
    for (let i = 0; i < 12; i++) {
        if (expensesByMonth[i] > incomeByMonth[i]) {
            incomeBorderColours.push('rgba(255, 0, 0, 1)');
        }
        else {
            incomeBorderColours.push('rgba(255, 0, 0, 0)');
        }
    }

    renderBarChart(barChart, incomeByMonth, expensesByMonth);
}

function renderBarChart(target, income, expenses) {
    const barData = {
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

    new Chart(barChart, {
        type: 'bar',
        data: barData,
        options: {
            plugins: {
                title: {
                    text: 'This year\'s balance' + currency,
                    display: true,
                    font: {
                        size: 16
                    }
                }
            }
        }
    });
}

function getCurrency() {
    let curr = document.getElementById("currency").innerHTML;

    if (curr == null) {
        curr = "";
    } else {
        curr = `, ${curr}`;
    }

    return curr;
}

const currency = getCurrency();
//TODO: better colours
const colours = ['rgba(139, 0, 0)', 'rgba(218, 165, 32, 1)', 'rgba(0, 255, 0 , 1)', 'rgba(32, 178, 170, 1)', 'rgba(0, 0, 255, 1)', 'rgba(200, 150, 0, 1)'];
const months = ['January', 'Febuary', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

let incomeBorderColours = [];

createBarChart();
createPieChart();