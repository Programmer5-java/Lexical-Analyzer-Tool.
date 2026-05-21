"""
Lexical Analyzer GUI with Export features

How to run:
1. Save this file as lexical_analyzer_gui_export.py
2. (Optional) To enable PDF export, install reportlab: pip install reportlab
3. Run: python lexical_analyzer_gui_export.py

Features added:
- Export Tokens to CSV
- Export Symbol Table to CSV
- Export combined Tokens+Symbol Table to PDF (uses reportlab if available). If reportlab is not installed, the app offers to save a plain text file instead.

This file builds on the improved lexer and colorful Tkinter GUI.
"""

import re
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import io

# Try import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# ----------------- Lexer (same as improved) -----------------
C_KEYWORDS = set('''auto break case char const continue default do double else enum extern float for goto if inline int long register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while _Bool _Complex _Imaginary'''.split())

TOKEN_SPEC = [
    ('COMMENT_MULTI', r'/\*.*?\*/'),
    ('COMMENT_SINGLE', r'//[^\n]*'),
    ('PREPROCESSOR', r'\#\s*[A-Za-z_]+(?:[^\n]*)'),
    ('HEADER_BRACKET', r'<[^>\n]*>'),
    ('STRING',   r'"(\\.|[^"\\])*"'),
    ('CHAR',     r"'(?:\\.|[^'\\])'"),
    ('NUMBER',   r'\b\d+(?:\.\d+)?\b'),
    ('IDENT',    r'\b[A-Za-z_]\w*\b'),
    ('OP',       r'\+\+|--|==|!=|>=|<=|<<|>>|\+=|-=|\*=|/=|%=|&&|\|\||->|[+\-*/%<>=&|^~!]|='),
    ('PUNC',     r'[;,(){}\[\].#]'),
    ('NEWLINE',  r'\n'),
    ('SKIP',     r'[ \t]+'),
    ('MISMATCH', r'.'),
]
MASTER_RE = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC), re.DOTALL)


def preprocess_logical_lines(code):
    code = code.replace('\r\n', '\n').replace('\r', '\n')
    code = code.replace('\\\n', ' ')
    return code


def improved_c_lexer(code):
    code = preprocess_logical_lines(code)
    tokens = []
    lineno = 1
    pos = 0
    while pos < len(code):
        m = MASTER_RE.match(code, pos)
        if not m:
            break
        kind = m.lastgroup
        text = m.group(kind)
        if kind == 'NEWLINE':
            lineno += 1
        elif kind == 'SKIP':
            pass
        elif kind == 'MISMATCH':
            tokens.append((lineno, text, 'Unknown'))
        else:
            token_type = kind
            if kind == 'IDENT':
                token_type = 'Keyword' if text in C_KEYWORDS else 'Identifier'
            elif kind == 'NUMBER':
                token_type = 'Number'
            elif kind in ('STRING', 'CHAR'):
                token_type = 'Literal'
            elif kind == 'PREPROCESSOR':
                token_type = 'Preprocessor'
            elif kind in ('COMMENT_MULTI', 'COMMENT_SINGLE'):
                token_type = 'Comment'
            elif kind == 'HEADER_BRACKET':
                token_type = 'Header'
            elif kind == 'OP':
                token_type = 'Operator'
            elif kind == 'PUNC':
                token_type = 'Punctuation'
            tokens.append((lineno, text, token_type))
            lineno += text.count('\n')
        pos = m.end()
    return tokens

# ----------------- CODE OPTIMIZATION (ADDED) -----------------
def optimize_code(source):
    lines = source.splitlines()
    constants = {}
    optimized = []

    for line in lines:
        stripped = line.strip()

        # Constant assignment
        m = re.match(r'(int|float|double|char)\s+(\w+)\s*=\s*(\d+)\s*;', stripped)
        if m:
            _, var, val = m.groups()
            constants[var] = val
            optimized.append(line)
            continue

        # Constant propagation
        for var, val in constants.items():
            line = re.sub(rf'\b{var}\b', val, line)

        # Constant folding
        exprs = re.findall(r'(\d+\s*[\+\-\*/]\s*\d+)', line)
        for e in exprs:
            try:
                line = line.replace(e, str(eval(e)))
            except:
                pass

        # Dead code elimination
        if re.search(r'if\s*\(\s*0\s*\)', line):
            optimized.append('// Dead code removed')
            continue

        # Strength reduction
        line = re.sub(r'(\w+)\s*\*\s*2', r'\1 << 1', line)

        optimized.append(line)

    return "\n".join(optimized)

# ----------------- GUI with Export -----------------
class LexicalAnalyzerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Lexical analyzer')
        self.geometry('1000x640')
        self.configure(bg='#dff4ff')
        self._create_widgets()
        self.symbol_table = {}

    def _create_widgets(self):
        left_frame = tk.Frame(self, bg='#bff0ff', bd=2, relief='groove')
        right_frame = tk.Frame(self, bg='#7ef1ef', bd=2, relief='groove')
        left_frame.place(relx=0.02, rely=0.03, relwidth=0.6, relheight=0.82)
        right_frame.place(relx=0.64, rely=0.03, relwidth=0.34, relheight=0.82)

        tk.Label(left_frame, text='Source Code', font=('Helvetica', 16, 'bold'), bg='#37d7f0').pack(fill='x')
        tk.Label(right_frame, text='Tokenize', font=('Helvetica', 16, 'bold'), bg='#37d7f0').pack(fill='x')

        text_frame = tk.Frame(left_frame)
        text_frame.pack(fill='both', expand=True, padx=8, pady=8)
        self.src_text = tk.Text(text_frame, wrap='none', font=('Consolas', 11), bg='white')
        self.src_text.pack(side='left', fill='both', expand=True)
        yscroll = tk.Scrollbar(text_frame, command=self.src_text.yview)
        yscroll.pack(side='right', fill='y')
        self.src_text['yscrollcommand'] = yscroll.set

        tree_frame = tk.Frame(right_frame)
        tree_frame.pack(fill='both', expand=True, padx=8, pady=8)
        cols = ('Line', 'Token', 'Type')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=20)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor='center')
        self.tree.pack(fill='both', expand=True)

        # Buttons
        btn_frame = tk.Frame(self, bg='#dff4ff')
        btn_frame.place(relx=0.02, rely=0.86, relwidth=0.96, relheight=0.11)

        tk.Button(btn_frame, text='Analyze', command=self.analyze, bg='#89d6ff', width=12).pack(side='left', padx=8, pady=6)
        tk.Button(btn_frame, text='Clear Source code', command=self.clear_source, bg='#89d6ff', width=16).pack(side='left', padx=8)
        tk.Button(btn_frame, text='Clear tokenize', command=self.clear_tokens, bg='#89d6ff', width=16).pack(side='left', padx=8)
        tk.Button(btn_frame, text='Symbol Table', command=self.show_symbol_table, bg='#89d6ff', width=12).pack(side='left', padx=8)
        tk.Button(btn_frame, text='Open File', command=self.open_file, bg='#c3f5d7', width=12).pack(side='right', padx=8)
        tk.Button(btn_frame, text='Save Source', command=self.save_source, bg='#c3f5d7', width=12).pack(side='right')
        tk.Button(btn_frame, text='Optimize Code', command=self.show_optimized_code, bg='#ffb347', width=14).pack(side='left', padx=8)

        # Export buttons (CSV/PDF)
        tk.Button(btn_frame, text='Export Tokens CSV', command=self.export_tokens_csv, bg='#cfe7ff', width=16).pack(side='right', padx=8)
        tk.Button(btn_frame, text='Export Symbols CSV', command=self.export_symbols_csv, bg='#cfe7ff', width=16).pack(side='right')
        tk.Button(btn_frame, text='Export PDF (Tokens+Symbols)', command=self.export_to_pdf, bg='#ffdca8', width=24).pack(side='left', padx=8)

        tk.Button(left_frame, text='Load Sample', command=self.load_sample, bg='#ffd98f').place(relx=0.02, rely=0.92)

    def analyze(self):
        code = self.src_text.get('1.0', 'end-1c')
        if not code.strip():
            messagebox.showinfo('Info', 'Please paste or write some source code first.')
            return
        tokens = improved_c_lexer(code)
        self.clear_tokens()
        for ln, tok, ttype in tokens:
            display_tok = tok.replace('\n', '\\n')
            if len(display_tok) > 60:
                display_tok = display_tok[:57] + '...'
            self.tree.insert('', 'end', values=(ln, display_tok, ttype))
        # build symbol table
        self.symbol_table = {}
        for ln, tok, ttype in tokens:
            if ttype == 'Identifier':
                dtype = self._guess_type_before(code, ln, tok)
                if tok not in self.symbol_table:
                    self.symbol_table[tok] = {'Data Type': dtype or 'N/A', 'Value': 'N/A'}
        messagebox.showinfo('Analysis Complete', f'{len(tokens)} tokens found. {len(self.symbol_table)} identifiers in symbol table.')

    def show_optimized_code(self):
        code = self.src_text.get('1.0', 'end-1c')
        optimized = optimize_code(code)

        win = tk.Toplevel(self)
        win.title('Optimized Code')
        txt = tk.Text(win, font=('Consolas', 11), bg='#f4fff4')
        txt.pack(fill='both', expand=True)
        txt.insert('1.0', optimized)

    def _guess_type_before(self, code, lineno, identifier):
        lines = code.splitlines()
        if lineno-1 < 0 or lineno-1 >= len(lines):
            return None
        line = lines[lineno-1]
        idx = line.find(identifier)
        if idx == -1:
            return None
        left = line[:idx]
        for t in ['int', 'float', 'double', 'char', 'long', 'short']:
            if re.search(r'\b' + re.escape(t) + r'\b', left):
                return t
        return None

    def clear_source(self):
        self.src_text.delete('1.0', 'end')

    def clear_tokens(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def show_symbol_table(self):
        win = tk.Toplevel(self)
        win.title('Symbol Table')
        win.geometry('520x360')
        win.configure(bg='#e6f2ff')

        tk.Label(win, text='Symbol Table:', font=('Helvetica', 14, 'bold'), bg='#7da9ff').pack(fill='x', pady=8)
        cols = ('Identifier', 'Data Type', 'Value')
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor='center')
        tree.pack(fill='both', expand=True, padx=12, pady=12)

        if not self.symbol_table:
            placeholder = ['year', 'Enter', 'a', 'd', 'is', 'leap', 'not']
            for p in placeholder:
                tree.insert('', 'end', values=(p, 'N/A', 'N/A'))
        else:
            for ident, info in self.symbol_table.items():
                tree.insert('', 'end', values=(ident, info.get('Data Type', 'N/A'), info.get('Value', 'N/A')))

        tk.Button(win, text='Close', command=win.destroy, bg='#ffd2d2').pack(pady=6)

    def load_sample(self):
        sample = ("""#include <stdio.h>
#define SQR(x) \
    ((x)*(x))

int main() {
    // single line comment
    /* multi-line
       comment example */
    int a = 15;
    int i;
    if(a>0)
    {
        printf("Positive Number\\n");
    }
    else if(a<0)
    {
        printf("Negative Number\\n");
    }
    else
    {
        printf("Zero\\n");
    }
    for(i=0; i<=100; i++)
    {
        printf("Bangladesh\\n");
    }
    return 0;
}
""")
        self.src_text.delete('1.0', 'end')
        self.src_text.insert('1.0', sample)

    def open_file(self):
        fname = filedialog.askopenfilename(filetypes=[('C files','*.c'),('Text files','*.txt'),('All files','*.*')])
        if not fname:
            return
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                data = f.read()
            self.src_text.delete('1.0', 'end')
            self.src_text.insert('1.0', data)
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def save_source(self):
        fname = filedialog.asksaveasfilename(defaultextension='.c', filetypes=[('C files','*.c'),('Text files','*.txt')])
        if not fname:
            return
        try:
            data = self.src_text.get('1.0', 'end-1c')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(data)
            messagebox.showinfo('Saved', f'Saved to {fname}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    # ----------------- Export helpers -----------------
    def _get_current_tokens(self):
        # Return tokens list by re-tokenizing current source
        code = self.src_text.get('1.0', 'end-1c')
        return improved_c_lexer(code)

    def export_tokens_csv(self):
        tokens = self._get_current_tokens()
        if not tokens:
            messagebox.showinfo('Info', 'No tokens to export. Please analyze source first.')
            return
        fname = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files','*.csv')])
        if not fname:
            return
        try:
            with open(fname, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Line', 'Token', 'Type'])
                for ln, tok, ttype in tokens:
                    writer.writerow([ln, tok, ttype])
            messagebox.showinfo('Saved', f'Tokens exported to {fname}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def export_symbols_csv(self):
        # ensure symbol table up to date
        tokens = self._get_current_tokens()
        self.symbol_table = {}
        code = self.src_text.get('1.0', 'end-1c')
        for ln, tok, ttype in tokens:
            if ttype == 'Identifier':
                dtype = self._guess_type_before(code, ln, tok)
                if tok not in self.symbol_table:
                    self.symbol_table[tok] = {'Data Type': dtype or 'N/A', 'Value': 'N/A'}
        if not self.symbol_table:
            messagebox.showinfo('Info', 'No symbols to export. Please analyze source first.')
            return
        fname = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files','*.csv')])
        if not fname:
            return
        try:
            with open(fname, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Identifier', 'Data Type', 'Value'])
                for ident, info in self.symbol_table.items():
                    writer.writerow([ident, info.get('Data Type', 'N/A'), info.get('Value', 'N/A')])
            messagebox.showinfo('Saved', f'Symbol table exported to {fname}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def export_to_pdf(self):
        tokens = self._get_current_tokens()
        # refresh symbol table
        self.symbol_table = {}
        code = self.src_text.get('1.0', 'end-1c')
        for ln, tok, ttype in tokens:
            if ttype == 'Identifier' and tok not in self.symbol_table:
                dtype = self._guess_type_before(code, ln, tok)
                self.symbol_table[tok] = {'Data Type': dtype or 'N/A', 'Value': 'N/A'}

        if not tokens and not self.symbol_table:
            messagebox.showinfo('Info', 'Nothing to export. Analyze source first.')
            return

        fname = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF files','*.pdf')])
        if not fname:
            return

        if REPORTLAB_AVAILABLE:
            try:
                c = canvas.Canvas(fname, pagesize=letter)
                width, height = letter
                x_margin = 40
                y = height - 40
                c.setFont('Helvetica-Bold', 14)
                c.drawString(x_margin, y, 'Lexical Analysis Report')
                y -= 24
                c.setFont('Helvetica', 10)
                c.drawString(x_margin, y, 'Tokens:')
                y -= 16
                c.setFont('Courier', 8)
                # tokens table header
                c.drawString(x_margin, y, 'Line')
                c.drawString(x_margin+60, y, 'Token')
                c.drawString(x_margin+420, y, 'Type')
                y -= 12
                c.line(x_margin, y, width - x_margin, y)
                y -= 12
                for ln, tok, ttype in tokens:
                    if y < 60:
                        c.showPage()
                        y = height - 40
                        c.setFont('Courier', 8)
                    tok_display = tok.replace('\n', '\\n')
                    if len(tok_display) > 60:
                        tok_display = tok_display[:57] + '...'
                    c.drawString(x_margin, y, str(ln))
                    c.drawString(x_margin+60, y, tok_display)
                    c.drawString(x_margin+420, y, ttype)
                    y -= 12
                # Symbol table
                if self.symbol_table:
                    if y < 120:
                        c.showPage()
                        y = height - 40
                    y -= 12
                    c.setFont('Helvetica', 10)
                    c.drawString(x_margin, y, 'Symbol Table:')
                    y -= 14
                    c.setFont('Courier', 9)
                    c.drawString(x_margin, y, 'Identifier')
                    c.drawString(x_margin+200, y, 'Data Type')
                    c.drawString(x_margin+320, y, 'Value')
                    y -= 12
                    c.line(x_margin, y, width - x_margin, y)
                    y -= 12
                    for ident, info in self.symbol_table.items():
                        if y < 60:
                            c.showPage()
                            y = height - 40
                        c.drawString(x_margin, y, ident)
                        c.drawString(x_margin+200, y, info.get('Data Type', 'N/A'))
                        c.drawString(x_margin+320, y, info.get('Value', 'N/A'))
                        y -= 12
                c.save()
                messagebox.showinfo('Saved', f'PDF report saved to {fname}')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to create PDF: {e}')
        else:
            # fallback: save a plain text report if reportlab not available
            fallback = messagebox.askyesno('Reportlab not found', 'reportlab is not installed. Save as plain text instead? (Yes -> .txt)')
            if not fallback:
                return
            txt_fname = fname[:-4] + '.txt' if fname.lower().endswith('.pdf') else fname + '.txt'
            try:
                with open(txt_fname, 'w', encoding='utf-8') as f:
                    f.write('Lexical Analysis Report\n')
                    f.write('--- Tokens ---\n')
                    for ln, tok, ttype in tokens:
                        f.write(f'{ln}\t{tok.replace("\n", "\\n")}\t{ttype}\n')
                    f.write('\n--- Symbol Table ---\n')
                    for ident, info in self.symbol_table.items():
                        f.write(f'{ident}\t{info.get("Data Type", "N/A")}\t{info.get("Value", "N/A")}\n')
                messagebox.showinfo('Saved', f'Text report saved to {txt_fname}')
            except Exception as e:
                messagebox.showerror('Error', str(e))


if __name__ == '__main__':
    app = LexicalAnalyzerGUI()
    app.mainloop()
