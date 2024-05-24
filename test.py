import tkinter as tk

def calculate_salary():
    hours_worked = float(hours_entry.get())
    hourly_rate = float(rate_entry.get())
    salary = hours_worked * hourly_rate
    result_label.config(text="Заробітна плата: {:.2f} грн".format(salary))

root = tk.Tk()
root.title("Система розрахунку заробітної плати")
hours_label = tk.Label(root, text="Години роботи:")
hours_label.pack()
hours_entry = tk.Entry(root)
hours_entry.pack()

rate_label = tk.Label(root, text="Погодинна ставка:")
rate_label.pack()
rate_entry = tk.Entry(root)
rate_entry.pack()

calculate_button = tk.Button(root, text="Розрахувати", command=calculate_salary)
calculate_button.pack()

result_label = tk.Label(root, text="")
result_label.pack()

root.mainloop()