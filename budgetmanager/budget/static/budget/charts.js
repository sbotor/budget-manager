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
                borderColor: 'rgba(0, 255, 0, 0)',
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

    new Chart(target, {
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
const colours = ['rgba(114, 147, 203, 1)', 'rgba(225, 151, 76, 1)', 'rgba(132, 186, 91 , 1)', 'rgba(211, 94, 96, 1)', 'rgba(128, 133, 133, 1)', 'rgba(144, 103, 167, 1)', 'rgba(171, 104, 87, 1)', 'rgba(204, 194, 16, 1)'];
const months = ['January', 'Febuary', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

createBarChart();
createPieChart();