from flask import Flask
from flask import Markup
from flask import Flask
from flask import render_template
app = Flask(__name__)
 
@app.route('/chart')
def chart():
    bar_chart = pygal.HorizontalStackedBar()
    bar_chart.title = "Remarquable sequences"
    bar_chart.x_labels = map(str, range(11))
    bar_chart.add('Fibonacci', [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55])
    bar_chart.add('Padovan', [1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12]) 
    chart = bar_chart.render(is_unicode=True)
    return render_template('chart.html', chart=chart )
 
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
