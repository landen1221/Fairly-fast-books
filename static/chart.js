// https://www.chartjs.org/

const myCategories = document.querySelectorAll(".categories")
const catAmounts = document.querySelectorAll(".cat-values")
const colors = [
'#bada55',
'#7fe5f0',
'#ff0000',
'#407294',
'#420420',
'#133337',
'#065535',
'#c0c0c0',
'#5ac18e',
'#f7347a',
'#ffc0cb',
'#008080',
'#ffd700',
'#cbcba9',
'#e6e6fa',
'#ffa500',
'#ff80ed',
'#696969',
'#ff7373',
'#0000ff',
'#003366',
'#800000',
'#c39797',
'#800080',
'#ccff00',
'#66cdaa',
'#ff6666',
'#ff00ff',
'#4ca3dd',
'#ffdab9',
'#ff7f50',
'#468499',
'#c0d6e4',
'#f6546a',
'#afeeee',
'#008000',
'#660066',
'#00ced1'
];

let myLabels = []
let myAmounts = []
let myColors = []

for (let i=0; i < myCategories.length; i++) {
    myLabels.push(myCategories[i].innerText)
    myColors.push(colors[i])
    let tempAmount = catAmounts[i].innerText.slice(1)
    myAmounts.push(parseInt(catAmounts[i].innerText.slice(1).replace(',', '')))
}


for (let i=1; i < myCategories.length+1; i++) {
    document.getElementById(`square-${i}`).style.color = myColors[i-1]
}

const barArea = document.getElementById('barChart');
const barChart = new Chart(barArea, {
    type: 'bar',
    data: {
        labels: myLabels,
        datasets: [{
            label: 'Amount Spent by category',
            data: myAmounts,
            backgroundColor: myColors,
            borderColor: myColors,
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            yAxes: [{
                ticks: {
                    beginAtZero: true
                }
            }]
        }
    }
});

const totalSpent = myAmounts.reduce(function(acc, nextV) {
    return acc + nextV
});

const pieAmounts = myAmounts.map(function(value) {
    return parseInt(value / totalSpent * 100)
});

const pieArea = document.getElementById('pieChart');
const pieChart = new Chart(pieArea, {
    type: 'pie',
    options: {
        legend: {
            display: false
        }
    },
    
    data: {
        labels: myLabels,
        datasets: [{
            label: 'myLabels',
            data: pieAmounts,
            backgroundColor: myColors,
            borderColor: myColors,
            borderWidth: 1
        }]
    },   
});

