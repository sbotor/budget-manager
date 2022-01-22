function addToData(data, labelInfo, amount) {
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

function renderChart(target, chartData, title) {
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
                    text: title,
                    display: true,
                    font: {
                        size: 16
                    }
                }
            }
        }
    })
}

const pieIncome = document.getElementById('pieIncome').getContext('2d');
const pieExpenses = document.getElementById('pieExpenses').getContext('2d');

//TODO: better colours
const colours = ['rgba(139, 0, 0)', 'rgba(218, 165, 32, 1)', 'rgba(0, 255, 0 , 1)', 'rgba(32, 178, 170, 1)', 'rgba(0, 0, 255, 1)', 'rgba(200, 150, 0, 1)'];

let incomeData = {}
let expensesData = {}

const opData = JSON.parse(document.getElementById('operationData').innerHTML);
opData.forEach(element => {
    const op = JSON.parse(element);

    const opAmount = parseFloat(op.amount);
    const labelInfo = op.label

    if (opAmount > 0) {
        addToData(incomeData, labelInfo, opAmount);
    } else {
        addToData(expensesData, labelInfo, opAmount);
    }
});

renderChart(pieIncome, incomeData, "This month's income");
renderChart(pieExpenses, expensesData, "This month's expenses");