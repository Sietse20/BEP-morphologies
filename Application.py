import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import os
import sys
import Converter_utils

class LogRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, text):
        self.widget.configure(state='normal')  # Ensure widget is writable
        self.widget.insert('end', text)
        self.widget.see('end')  # Scroll to the end of the text
        self.widget.configure(state='disabled')  # Disable widget again
        self.flush()  # Flush after each write

    def flush(self):
        self.widget.update_idletasks()  # Update the GUI immediately

class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SWC to NeuroML Converter")
        self.root.geometry("500x300")

        self.log_window = None
        self.create_log_window()

        # Redirect stdout and stderr to the log window
        sys.stdout = LogRedirector(self.log_text)
        sys.stderr = LogRedirector(self.log_text)

        self.main_menu()

    def main_menu(self):
        self.clear_window()

        tk.Label(self.root, text="Choose a functionality:", font=("Arial", 14)).pack(pady=20)

        tk.Button(self.root, text="Single File", command=self.single_file_window, font=("Arial", 12)).pack(fill='x', pady=10)
        tk.Button(self.root, text="Directory", command=self.directory_window, font=("Arial", 12)).pack(fill='x', pady=10)
        tk.Button(self.root, text="API", command=self.api_window, font=("Arial", 12)).pack(fill='x', pady=10)
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            if widget != self.log_window:
                widget.destroy()

    def show_back_button(self):
        tk.Button(self.root, text="Back", command=self.main_menu, font=("Arial", 12)).pack(anchor='w', pady=10)

    def single_file_window(self):
        self.clear_window()
        self.show_back_button()

        tk.Label(self.root, text="Single File Conversion", font=("Arial", 14)).pack(pady=10)
        
        self.swc_file_path = tk.StringVar()
        self.output_directory = tk.StringVar()

        self.create_file_chooser("Select SWC File:", self.swc_file_path)
        self.create_directory_chooser("Select Output Directory (optional):", self.output_directory)

        tk.Button(self.root, text="Start Conversion", command=self.start_single_file_conversion, font=("Arial", 12)).pack(pady=20)

    def create_file_chooser(self, title, variable):
        frame = tk.Frame(self.root)
        frame.pack(fill='x', pady=5)
        
        tk.Label(frame, text=title, font=("Arial", 12)).pack(side='left', padx=5)
        tk.Button(frame, text="Browse", command=lambda: self.choose_file(variable), font=("Arial", 12)).pack(side='left', padx=5)
        tk.Entry(frame, textvariable=variable, font=("Arial", 12), state='readonly', width=40).pack(side='left', padx=5)

    def create_directory_chooser(self, title, variable):
        frame = tk.Frame(self.root)
        frame.pack(fill='x', pady=5)
        
        tk.Label(frame, text=title, font=("Arial", 12)).pack(side='left', padx=5)
        tk.Button(frame, text="Browse", command=lambda: self.choose_directory(variable), font=("Arial", 12)).pack(side='left', padx=5)
        tk.Entry(frame, textvariable=variable, font=("Arial", 12), state='readonly', width=40).pack(side='left', padx=5)

    def choose_file(self, variable):
        file_path = filedialog.askopenfilename(title="Select SWC File", filetypes=[("SWC files", "*.swc")])
        if file_path:
            if not file_path.endswith('.swc'):
                messagebox.showerror("Invalid File", "Please choose a file with a .swc extension")
            else:
                variable.set(file_path)

    def choose_directory(self, variable):
        dir_path = filedialog.askdirectory(title="Select Directory")
        if dir_path:
            variable.set(dir_path)

    def start_single_file_conversion(self):
        swc_file_path = self.swc_file_path.get()
        output_directory = self.output_directory.get() if self.output_directory.get() else None
        
        if swc_file_path:
            self.show_log_window()
            self.convert_single_file(swc_file_path, output_directory)
        else:
            messagebox.showwarning("Input Error", "Please choose an SWC file.")

    def directory_window(self):
        self.clear_window()
        self.show_back_button()

        tk.Label(self.root, text="Directory Conversion", font=("Arial", 14)).pack(pady=10)
        
        self.directory_path = tk.StringVar()
        self.print_errors = tk.BooleanVar()
        self.output_directory = tk.StringVar()

        self.create_directory_chooser("Select Directory:", self.directory_path)
        tk.Checkbutton(self.root, text="Print Errors", variable=self.print_errors, font=("Arial", 12)).pack(pady=5)
        self.create_directory_chooser("Select Output Directory (optional):", self.output_directory)

        tk.Button(self.root, text="Start Conversion", command=self.start_directory_conversion, font=("Arial", 12)).pack(pady=20)

    def start_directory_conversion(self):
        directory_path = self.directory_path.get()
        print_errors = self.print_errors.get()
        output_directory = self.output_directory.get() if self.output_directory.get() else None
        
        if directory_path:
            self.show_log_window()
            self.convert_directory(directory_path, print_errors, output_directory)
        else:
            messagebox.showwarning("Input Error", "Please choose a directory.")

    def api_window(self):
        self.clear_window()
        self.show_back_button()

        tk.Label(self.root, text="API Conversion", font=("Arial", 14)).pack(pady=10)
        
        self.page_range_start = tk.IntVar()
        self.page_range_end = tk.IntVar()
        self.size = tk.IntVar()
        self.print_errors = tk.BooleanVar()
        self.output_directory = tk.StringVar()

        self.create_page_range_chooser("Page Range:", self.page_range_start, self.page_range_end)
        self.create_labeled_entry("Size:", self.size)
        
        tk.Checkbutton(self.root, text="Print Errors", variable=self.print_errors, font=("Arial", 12)).pack(pady=5)
        self.create_directory_chooser("Select Output Directory (optional):", self.output_directory)

        tk.Button(self.root, text="Start Conversion", command=self.start_api_conversion, font=("Arial", 12)).pack(pady=20)

    def create_page_range_chooser(self, label_text, start_variable, end_variable):
        frame = tk.Frame(self.root)
        frame.pack(fill='x', pady=5)
        
        tk.Label(frame, text=label_text, font=("Arial", 12)).pack(side='left', padx=5)
        tk.Entry(frame, textvariable=start_variable, font=("Arial", 12), width=5).pack(side='left', padx=2)
        tk.Label(frame, text="-", font=("Arial", 12)).pack(side='left')
        tk.Entry(frame, textvariable=end_variable, font=("Arial", 12), width=5).pack(side='left', padx=2)

    def create_labeled_entry(self, label_text, variable):
        frame = tk.Frame(self.root)
        frame.pack(fill='x', pady=5)
        
        tk.Label(frame, text=label_text, font=("Arial", 12)).pack(side='left', padx=5)
        tk.Entry(frame, textvariable=variable, font=("Arial", 12)).pack(side='left', padx=5, fill='x')

    def show_log_window(self):
        if self.log_window is not None and self.log_window.winfo_exists():
            self.log_window.deiconify()  # Show the log window
        else:
            self.create_log_window()

    def on_log_window_close(self):
        self.log_window.withdraw()  # Hide the log window instead of destroying it

    def create_log_window(self):
        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("Log")
        self.log_window.geometry("600x400+700+100")
        self.log_text = ScrolledText(self.log_window, state='normal', font=("Arial", 10))
        self.log_text.pack(expand=True, fill='both')
        self.log_window.protocol("WM_DELETE_WINDOW", self.on_log_window_close)
        self.log_window.withdraw()  # Start hidden

    def convert_single_file(self, swc_file_path, output_directory):
        if swc_file_path.endswith('.swc'):
            print(f"Converting single file: {swc_file_path} to {output_directory if output_directory else 'default directory'}")
            Converter_utils.convert_file(swc_file_path, output_dir=output_directory)
        else:
            messagebox.showerror("Invalid File", "Please choose a file with a .swc extension")

    def convert_directory(self, directory_path, print_errors, output_directory):
        print(f"Converting directory: {directory_path} with print errors set to {print_errors} to {output_directory if output_directory else 'default directory'}")
        Converter_utils.convert_directory(directory_path, print_errors, path_nml=output_directory)

    def convert_from_api(self, page_range, size, print_errors, output_directory):
        print(f"Converting from API with page range: {page_range}, size: {size}, print errors set to {print_errors}, output directory: {output_directory if output_directory else 'default directory'}")
        Converter_utils.convert_api_bulk(page_range, size, print_errors, output_dir_nml=output_directory)

    def start_api_conversion(self):
        page_range_start = self.page_range_start.get()
        page_range_end = self.page_range_end.get()
        size = self.size.get()
        print_errors = self.print_errors.get()
        output_directory = self.output_directory.get() if self.output_directory.get() else None
        
        if page_range_start and page_range_end:
            self.show_log_window()
            self.convert_from_api((page_range_start, page_range_end), size, print_errors, output_directory)
        else:
            messagebox.showwarning("Input Error", "Please enter both start and end page range values.")

# Example usage
if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()
