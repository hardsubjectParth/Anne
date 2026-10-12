# Sweet / Anne — Complete User Guide, Internals, Features, and Examples

You've provided a complete setup script for **Sweet**, a small compiler and execution engine for **Anne**, a dataset-oriented programming language built on top of Polars.

The best way to understand this project is to think of it as a small data-processing language that lets you manipulate CSV, Parquet, JSON, Excel, and other supported datasets using readable expressions rather than writing Python for every operation.

For example, instead of writing a Python program to load sales data, filter expensive products, calculate revenue, group by region, and export a report, you can write:

```
data sales = read "sales.csv";

data report = sales
    .filter(price > 100)
    .derive(revenue = price * quantity)
    .group_by(region)
    .summarize(
        total_revenue = sum(revenue),
        average_revenue = mean(revenue),
        number_of_sales = count()
    )
    .sort(total_revenue, desc);

report.show();
report.save("regional_report.csv");
```

Sweet processes this program, checks it for errors, converts it into a logical execution plan, optimizes that plan, and executes it using Polars.

**The central idea is that Anne describes what you want to do, while Sweet handles how the operations are compiled and executed.**

This guide covers:

1. What Sweet and Anne are.
2. Installing and running the project.
3. Writing your first Anne programs.
4. All supported language features and methods.
5. Loading, transforming, grouping, joining, and exporting datasets.
6. The compiler architecture and internal implementation.
7. Lazy execution and optimization.
8. The REPL, CLI, errors, and debugging.
9. Testing, extending, and improving the project.
10. Important limitations and implementation details in your current code.

One important distinction: your message contains the setup script, not a report from an actual installation. I'll explain what the supplied implementation is designed to do and point out places where the code needs attention. I won't assume that the installation, tests, or demo have successfully completed on your machine.

---

# 1\. Understanding Sweet and Anne

## 1.1 What is Anne?

Anne is the language that you write.

It provides a compact syntax for expressing dataset operations:

```
data employees = read "employees.csv";

data engineers = employees
    .filter(department == "Engineering")
    .select(name, salary)
    .sort(salary, desc);

engineers.show();
```

This program defines a dataset, filters its rows, selects two columns, sorts the result, and displays it.

Anne is a domain-specific language, or DSL.

A DSL is a programming language designed for a particular problem domain. Examples of domains include querying databases, describing infrastructure, processing images, and manipulating datasets.

Anne's domain is dataset processing.

Its syntax is inspired by method chaining and dataframe libraries, but it is not Python. You cannot directly use arbitrary Python statements, Python functions, imports, loops, or classes inside an Anne program.

## 1.2 What is Sweet?

Sweet is the software that makes Anne work.

Your implementation contains several components:

- A parser that recognizes Anne syntax.
- An abstract syntax tree, or AST, that represents the program.
- A semantic analyzer that checks whether the program makes sense.
- A dataset abstraction that tracks schemas and logical plans.
- An intermediate representation, or IR, for expressions and operations.
- An optimizer that simplifies certain operations.
- A Polars backend that translates the plan into executable operations.
- An executor that performs actions and writes output.
- A command-line interface and an interactive REPL.

These components work together to turn Anne source code into actual data processing.

## 1.3 How Sweet differs from writing Polars directly

Consider the equivalent operations in Python and Anne.

**Python with Polars:**

```
import polars as pl

sales = pl.scan_csv("sales.csv")

report = (
    sales
    .filter(pl.col("price") > 100)
    .with_columns(
        (pl.col("price") * pl.col("quantity")).alias("revenue")
    )
    .group_by("region")
    .agg(
        pl.col("revenue").sum().alias("total_revenue")
    )
    .sort("total_revenue", descending=True)
)

print(report.collect())
```

**Anne:**

```
data sales = read "sales.csv";

data report = sales
    .filter(price > 100)
    .derive(revenue = price * quantity)
    .group_by(region)
    .summarize(total_revenue = sum(revenue))
    .sort(total_revenue, desc);

report.show();
```

Anne hides the Python imports, Polars expression syntax, aliases, and explicit materialization calls in the common workflow.

Sweet generates the underlying operations for you.

There is an important limitation, however: Sweet is currently a small language with a defined set of operations, not a general-purpose replacement for Python or a complete SQL engine.

---

# 2\. Understanding Your Installation Script

Your script is named `setup_sweet.sh`.

It creates the project directory, generates the source files, installs the dependencies, runs tests, executes an example, and creates a convenient command-line launcher.

## 2.1 What happens when you execute it?

The intended sequence is:

| Stage | What happens |
| --- | --- |
| 1 | Find Python 3.10 or newer. |
| 2 | Create the `anne-sweet` project and generate its files. |
| 3 | Create a virtual environment and install dependencies. |
| 4 | Run the pytest test suite. |
| 5 | Execute the example Anne program. |
| 6 | Link the `sweet` command into `~/.local/bin`. |

The script starts with:

```
set -euo pipefail
```

This enables stricter Bash error handling.

In particular, `-e` generally causes the script to stop when a command fails. This means a failing test suite should prevent the later demo and PATH setup stages from running.

## 2.2 Where is the project created?

This line controls the location:

```
PROJ="${PROJ:-$PWD/anne-sweet}"
```

If you execute the script from:

```
/home/user/
```

the default project directory becomes:

```
/home/user/anne-sweet/
```

You can override the location:

```
PROJ="$HOME/projects/anne-sweet" bash setup_sweet.sh
```

Use a directory that does not contain work you need to preserve.

**Important:** the script automatically renames an existing project directory to a timestamped backup before creating a replacement. It does not update an existing installation in place.

For example, it may rename:

```
anne-sweet/
```

to:

```
anne-sweet.bak.1791710000/
```

The timestamp is illustrative. The actual value depends on when the script runs.

## 2.3 Which dependencies are installed?

Your `pyproject.toml` declares:

| Dependency | Purpose |
| --- | --- |
| Python 3.10+ | Runs the compiler and CLI. |
| Polars | Performs dataframe and lazy-query operations. |
| Lark | Parses Anne source code using the grammar. |
| fastexcel | Supports Excel input through Polars. |
| pytest | Runs the tests. |
| xlsxwriter | Helps generate Excel files in tests and examples. |

The main dependencies are installed using:

```
python -m pip install -e ".[dev]"
```

The `-e` option installs the project in editable mode. This is useful during development because changes to the source files generally take effect without reinstalling the package.

The `.[dev]` part also installs the optional development dependencies.

## 2.4 How do you verify the installation?

After the setup script finishes, run:

```
cd anne-sweet
source .venv/bin/activate
```

Check the version:

```
sweet --version
```

Expected output:

```
sweet 0.1.0
```

Check the command-line help:

```
sweet --help
```

Run the tests again:

```
python -m pytest -q
```

If the `sweet` command is not found, try:

```
export PATH="$HOME/.local/bin:$PATH"
```

Then run:

```
sweet --version
```

The setup script adds this PATH configuration to `~/.bashrc` if it does not already find `.local/bin` there. A new shell may be required for that change to take effect automatically.

---

# 3\. Project Structure: Where Everything Lives

After running the setup script, your project should look approximately like this:

```
anne-sweet/
│
├── pyproject.toml
├── README.md
│
├── src/
│   └── sweet/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── compiler.py
│       ├── repl.py
│       │
│       ├── frontend/
│       │   ├── grammar.lark
│       │   ├── parser.py
│       │   ├── ast_builder.py
│       │   └── ast_nodes.py
│       │
│       ├── semantic/
│       │   ├── analyzer.py
│       │   ├── types.py
│       │   └── symbols.py
│       │
│       ├── objects/
│       │   ├── dataset.py
│       │   └── grouped_dataset.py
│       │
│       ├── ir/
│       │   ├── expressions.py
│       │   ├── plan_nodes.py
│       │   └── logical_plan.py
│       │
│       ├── optimizer/
│       │   ├── constant_folding.py
│       │   ├── filter_fusion.py
│       │   └── optimizer.py
│       │
│       ├── runtime/
│       │   ├── io.py
│       │   ├── expression_compiler.py
│       │   ├── polars_backend.py
│       │   └── executor.py
│       │
│       └── diagnostics/
│           └── errors.py
│
├── tests/
│   ├── conftest.py
│   ├── test_frontend.py
│   ├── test_semantics.py
│   ├── test_optimizer.py
│   └── test_end_to_end.py
│
└── examples/
    ├── sales.csv
    ├── customers.csv
    ├── orders.csv
    └── analysis.anne
```

The demo may also create `examples/results/` to hold exported files.

Here's what each major part does.

| Directory or file | Responsibility |
| --- | --- |
| `frontend/` | Understands Anne syntax and constructs the AST. |
| `semantic/` | Checks names, expressions, types, and program meaning. |
| `objects/` | Implements the language-level dataset abstractions. |
| `ir/` | Represents expressions and logical execution plans. |
| `optimizer/` | Simplifies expressions and combines adjacent filters. |
| `runtime/` | Reads files, compiles expressions to Polars, executes plans, and writes output. |
| `diagnostics/` | Represents errors and formats source-code locations and hints. |
| `compiler.py` | Connects the compilation stages. |
| `cli.py` | Implements the command-line interface. |
| `repl.py` | Implements interactive execution. |
| `tests/` | Tests parsing, semantic checks, optimization, and execution. |

### The most important files to understand first

If you want to understand the project without reading every file, start with these:

1. `src/sweet/compiler.py`
2. `src/sweet/frontend/grammar.lark`
3. `src/sweet/frontend/ast_nodes.py`
4. `src/sweet/semantic/analyzer.py`
5. `src/sweet/objects/dataset.py`
6. `src/sweet/ir/plan_nodes.py`
7. `src/sweet/optimizer/optimizer.py`
8. `src/sweet/runtime/polars_backend.py`
9. `src/sweet/runtime/executor.py`

Together, these explain almost the entire path from Anne source code to executed data operations.

---

# 4\. Running Anne Programs

Sweet provides three main ways to interact with Anne.

## 4.1 Run a program

Your setup script creates:

```
examples/analysis.anne
```

From the project root, run:

```
sweet examples/analysis.anne
```

This executes the program.

To choose the output directory for files explicitly exported using `save()`, use:

```
sweet examples/analysis.anne -o results
```

This is equivalent to:

```
sweet examples/analysis.anne --output results
```

For example, if your Anne program contains:

```
data sales = read "sales.csv";

data expensive = sales.filter(price > 1000);

expensive.save("expensive.csv");
```

and you run:

```
sweet examples/analysis.anne -o results
```

the exported file is intended to appear at:

```
results/expensive.csv
```

The relative input path `sales.csv` is resolved against the directory containing `analysis.anne`. The output path is resolved against the selected output directory.

This distinction is important: **input paths and output paths have different bases.**

## 4.2 Check a program without executing its actions

Use:

```
sweet examples/analysis.anne --check
```

This parses the program, performs semantic analysis, and builds the optimized logical plan.

It does not execute the resulting actions.

For example:

```
data sales = read "sales.csv";

data expensive = sales.filter(price > 1000);

expensive.show();
```

Under `--check`, Sweet validates the program but does not display the rows.

One subtlety: your implementation calls `schema_of()` when processing a `read` declaration. That means checking a program can still access the input file and inspect its schema. It is not a completely file-independent static check.

## 4.3 Start the interactive REPL

Run:

```
sweet
```

You should see a greeting similar to:

```
Anne REPL (sweet). :help for help.
anne>
```

Now enter:

```
data sales = read "examples/sales.csv";
```

Then:

```
sales.show();
```

You can issue more statements without restarting the process.

Useful commands include:

```
:help
:datasets
:reset
:quit
```

Their purposes are:

- `:help`: display the REPL help text.
- `:datasets`: list dataset bindings in the current session.
- `:reset`: create a fresh session.
- `:quit`: exit the REPL.

The REPL and the CLI use the same compiler and execution machinery. That is a useful architectural decision because language behavior is not intentionally implemented separately for interactive mode.

**REPL path note:** its session starts with the current working directory as its base directory. Consequently, `read "examples/sales.csv"` works when you start the REPL from the project root. If you start it elsewhere, adjust your paths or start it from the appropriate directory.

---

# 5\. Anne Language Fundamentals

Let's learn the language itself.

## 5.1 Statements end with semicolons

Every top-level statement must end with `;`.

Correct:

```
data sales = read "sales.csv";

sales.show();
```

Incorrect:

```
data sales = read "sales.csv"
```

The parser expects the statement terminator.

You can put several statements on one line:

```
data sales = read "sales.csv"; sales.show();
```

Or spread them across multiple lines:

```
data sales = read "sales.csv";

data expensive = sales
    .filter(price > 1000)
    .select(customer, price);

expensive.show();
```

Whitespace and newlines separate tokens, but they do not replace the semicolon.

## 5.2 Comments

Anne supports comments beginning with `#`.

```
# Load the sales dataset.
data sales = read "sales.csv";

# Keep expensive transactions.
data expensive = sales.filter(price > 1000);
```

Trailing comments are also supported:

```
data sales = read "sales.csv";  # Load sales
```

The grammar ignores comment text until the end of the line.

## 5.3 Dataset declarations

A declaration has this form:

```
data NAME = EXPRESSION;
```

For example:

```
data sales = read "sales.csv";

data expensive = sales.filter(price > 1000);

data north_sales = sales.filter(region == "north");
```

Each declaration creates a binding in the current symbol table.

The binding associates a name with a dataset object containing a logical plan and a schema.

### Bindings are immutable

You cannot redefine a dataset name within the same scope.

This is allowed:

```
data sales = read "sales.csv";

data expensive = sales.filter(price > 1000);

data affordable = sales.filter(price <= 1000);
```

This is not:

```
data sales = read "sales.csv";

data sales = sales.filter(price > 1000);
```

Sweet reports that the dataset has already been defined.

Use a new name whenever you want to represent a transformed dataset.

This is binding immutability, not a guarantee that the underlying file can never change. If a source file changes between executions, a lazy scan may observe different data.

## 5.4 Dataset names versus column names

These have different meanings:

```
data sales = read "sales.csv";
```

Here, `sales` is a dataset name.

Inside a dataset expression:

```
sales.filter(price > 1000);
```

`price` is a column name.

Sweet's analyzer resolves `sales` through the symbol table and resolves `price` against the dataset schema.

This distinction is important because a typo in either place produces a different kind of error.

---

# 6\. Reading Data

Reading data is the starting point for most programs.

## 6.1 Basic CSV input

```
data sales = read "sales.csv";
```

Your implementation uses a Polars lazy CSV scan for this format.

The expected CSV structure might be:

```
customer,region,quantity,price
alice,north,2,1500
bob,south,1,300
carol,north,5,120
```

Sweet inspects the file's schema and stores the discovered column names and inferred types.

It does not immediately need to load all rows into memory.

## 6.2 Supported input formats

Your `READ_FORMATS` dictionary recognizes these extensions:

| Extension | Reader |
| --- | --- |
| `.csv` | CSV |
| `.tsv` | CSV reader configured with a tab delimiter by default |
| `.parquet` | Parquet |
| `.json` | JSON |
| `.ndjson` | Newline-delimited JSON |
| `.jsonl` | Newline-delimited JSON |

It also supports:

```
.xlsx
```

for Excel input through Polars.

For example:

```
data sales = read "sales.csv";
data archive = read "archive.parquet";
data records = read "events.ndjson";
data workbook = read "report.xlsx";
```

The exact behavior and supported details depend on the installed Polars version and its optional dependencies.

## 6.3 Reader options

Anne allows options after `with`.

The grammar is:

```
data NAME = read "FILE" with (OPTION = VALUE, ...);
```

### Change a CSV delimiter

```
data sales = read "sales.csv" with (delimiter = ";");
```

For this input:

```
customer;price
alice;1500
bob;300
```

the semicolon separates the columns.

The delimiter must be a single character.

### Specify whether the file has a header

```
data raw = read "data.csv" with (header = false);
```

With `header = false`, the first row is treated as data rather than as a header. Polars generates column names.

### Read CSV columns as strings

```
data raw = read "sales.csv" with (infer_schema = false);
```

Your implementation sets `infer_schema_length=0` for this option, intending to read all columns as text.

This can be useful when importing inconsistent identifiers, codes with leading zeros, or files with irregular values.

Remember that numeric expressions then require appropriate conversion support. Your current language does not implement general-purpose casts, so reading everything as text limits subsequent arithmetic.

### Excel input

```
data workbook = read "report.xlsx";
```

You can specify a sheet:

```
data workbook = read "report.xlsx" with (sheet = "Sales");
```

You can also configure the header:

```
data workbook = read "report.xlsx" with (header = false);
```

### Options depend on the file format

The current implementation validates options against format-specific lists.

For CSV and TSV, it accepts:

- `header`
- `infer_schema`
- `delimiter`

For Excel, it accepts:

- `header`
- `sheet`

The other listed formats accept no additional reader options in this implementation.

For example, this should produce a semantic error:

```
data sales = read "sales.csv" with (sheet = "Sales");
```

The option is valid for Excel but not for CSV.

## 6.4 How input paths are resolved

Suppose your program is:

```
project/
├── examples/
│   ├── analysis.anne
│   └── sales.csv
```

When you run:

```
sweet examples/analysis.anne
```

the declaration:

```
data sales = read "sales.csv";
```

looks for:

```
project/examples/sales.csv
```

because `cli.py` constructs the session using the Anne program's parent directory.

For scripts, this is generally more convenient than resolving input paths against whichever directory the shell happens to be using.

---

# 7\. Filtering Rows

The `filter()` method keeps rows that satisfy a Boolean condition.

Example:

```
data sales = read "sales.csv";

data expensive = sales.filter(price > 1000);

expensive.show();
```

Only rows where `price > 1000` evaluates to true are retained.

You can combine conditions.

## 7.1 Comparison operators

Anne supports:

| Operator | Meaning | Example |
| --- | --- | --- |
| `==` | Equal | `price == 1000` |
| `!=` | Not equal | `region != "north"` |
| `>` | Greater than | `price > 1000` |
| `<` | Less than | `quantity < 5` |
| `>=` | Greater than or equal | `price >= 1000` |
| `<=` | Less than or equal | `price <= 1000` |

Examples:

```
data expensive = sales.filter(price > 1000);

data northern = sales.filter(region == "north");

data valid = sales.filter(quantity >= 1);

data not_north = sales.filter(region != "north");
```

## 7.2 Logical operators

Anne supports:

- `and`
- `or`
- `not`

Example:

```
data result = sales.filter(
    price > 1000 and quantity >= 2
);
```

Another example:

```
data result = sales.filter(
    region == "north" or region == "south"
);
```

Negation:

```
data result = sales.filter(
    not (price < 100)
);
```

Parentheses let you control the grouping of expressions.

## 7.3 Operator precedence

Your grammar establishes the following general precedence, from lower to higher:

1. `or`
2. `and`
3. `not`
4. Comparisons
5. Addition and subtraction
6. Multiplication, division, and remainder
7. Unary minus

For example:

```
data result = sales.filter(
    price + 10 * quantity > 100
);
```

The arithmetic expression is interpreted as:

```
price + (10 * quantity)
```

rather than:

```
(price + 10) * quantity
```

Likewise:

```
data result = sales.filter(
    price > 100 and quantity > 2 or region == "north"
);
```

groups as:

```
((price > 100) and (quantity > 2)) or (region == "north")
```

Use parentheses when the intended logic might not be immediately obvious.

## 7.4 What does filter() return?

It returns another `Dataset`, with the same schema and a new logical plan node.

It does not normally collect all rows immediately.

This is the foundation of Sweet's lazy execution model, which we will examine later.

---

# 8\. Selecting Columns

Use `select()` to retain only specified columns.

```
data sales = read "sales.csv";

data customer_prices = sales.select(customer, price);

customer_prices.show();
```

If the original dataset has:

```
customer, region, quantity, price
```

the selected dataset has:

```
customer, price
```

The order you specify is preserved.

For example:

```
data reordered = sales.select(price, customer, region);
```

produces the column order:

```
price, customer, region
```

The implementation requires at least one column:

```
sales.select();
```

is invalid.

Duplicate selections are also rejected:

```
sales.select(price, price);
```

And unknown columns produce an error:

```
sales.select(prcie);
```

Sweet attempts to suggest a likely correction:

```
unknown column 'prcie'
help: did you mean 'price'?
```

The exact rendered output depends on the error context.

---

# 9\. Creating and Modifying Columns with derive()

The `derive()` method computes new columns or replaces existing ones.

## 9.1 Create a calculated column

```
data sales = read "sales.csv";

data calculated = sales.derive(
    revenue = price * quantity
);
```

For each row, Sweet computes:

```
revenue = price × quantity
```

For example:

```
quantity = 2
price = 1500
revenue = 3000
```

You can create multiple columns in one call:

```
data calculated = sales.derive(
    revenue = price * quantity,
    discounted_price = price * 0.9,
    is_expensive = price > 1000
);
```

This creates three expressions.

The expressions are translated into Polars expressions and passed to `with_columns()`.

## 9.2 Replace an existing column

You can reuse an existing column name:

```
data adjusted = sales.derive(
    price = price * 1.1
);
```

This replaces the original `price` column with its adjusted value.

The schema retains the same column position but updates its inferred type if necessary.

## 9.3 Supported arithmetic

Your language supports:

```
data result = sales.derive(
    total = price * quantity,
    difference = price - quantity,
    combined = price + quantity,
    ratio = price / quantity,
    remainder = price % quantity
);
```

The operators are:

- `+`: addition; it also concatenates two strings.
- `-`: subtraction.
- `*`: multiplication.
- `/`: division.
- `%`: remainder.
- Unary `-`: numeric negation.

For example:

```
data result = sales.derive(
    label = customer + "!",
    negative_price = -price
);
```

The current type checker does not support every operation that Polars itself can perform. It deliberately restricts expressions to a smaller language.

## 9.4 A limitation: derive expressions use the original schema

Your `derive()` implementation lowers each expression against the schema of the dataset before the call.

Consequently, do not assume that a column created earlier in the same `derive()` call can be referenced by a later expression.

For example:

```
data result = sales.derive(
    revenue = price * quantity,
    tax = revenue * 0.18
);
```

Although this may look natural, `revenue` is not present in the original schema when Sweet analyzes `tax`.

It will be reported as an unknown column.

Use two calls instead:

```
data result = sales
    .derive(revenue = price * quantity)
    .derive(tax = revenue * 0.18);
```

The second call sees the schema produced by the first.

---

# 10\. Sorting, Limiting, and Removing Missing Values

## 10.1 Sorting

Use `sort()` to order rows by one or more columns.

Ascending:

```
data sorted = sales.sort(price);
```

Descending:

```
data sorted = sales.sort(price, desc);
```

Multiple columns:

```
data sorted = sales.sort(region, price, desc);
```

In this example:

- `region` is sorted ascending.
- `price` is sorted descending within each region.

The direction marker `desc` must directly follow a column name.

You can also write:

```
data sorted = sales.sort(price, desc, quantity, desc);
```

This sorts by `price` descending and then by `quantity` descending.

Your implementation supports `asc` and `desc` as special markers inside `sort()`.

They are not general-purpose language keywords for ordering arbitrary expressions.

## 10.2 Limit the number of rows

```
data first_five = sales.limit(5);
```

Aliases:

```
data first_five = sales.head(5);
```

Both methods use the same implementation.

A limit of zero is valid:

```
data empty = sales.limit(0);
```

A negative limit is rejected.

Importantly, `limit(5)` means the first five rows in the current logical sequence. If you want the five highest-priced rows, sort first:

```
data top_five = sales
    .sort(price, desc)
    .limit(5);
```

## 10.3 Get the last rows

```
data last_five = sales.tail(5);
```

This returns the final five rows of the current sequence.

## 10.4 Remove missing values

To remove rows with null values in any column:

```
data clean = sales.drop_missing();
```

To check only selected columns:

```
data clean = sales.drop_missing(price, quantity);
```

The current implementation uses Polars `drop_nulls()`.

**Important:** `drop_missing()` removes null values, not floating-point NaN values. NaN and null are different representations in Polars.

If your data contains NaNs, the current method will not necessarily remove those rows.

---

# 11\. Grouping and Aggregation

Grouping and aggregation are among the most useful features in Anne.

The basic pattern is:

```
data report = sales
    .group_by(region)
    .summarize(
        total = sum(price),
        average = mean(price),
        records = count()
    );
```

This produces one output row per region.

## 11.1 What group\_by() does

```
data grouped = sales.group_by(region);
```

This creates a `GroupedDataset`.

It represents a dataset together with its grouping keys.

It is not an ordinary dataset and cannot be displayed directly.

For example:

```
data grouped = sales.group_by(region);

grouped.show();
```

is rejected. You must summarize it first.

## 11.2 What summarize() does

The `summarize()` method computes aggregates for each group.

For example:

```
data report = sales
    .group_by(region)
    .summarize(
        total_price = sum(price),
        average_price = mean(price),
        maximum_price = max(price),
        minimum_price = min(price),
        transactions = count()
    );
```

The output schema is conceptually:

```
region
total_price
average_price
maximum_price
minimum_price
transactions
```

Each group produces a row containing the calculated values.

## 11.3 Supported aggregate functions

Your implementation supports six aggregate functions.

| Function | Meaning |
| --- | --- |
| `sum(column)` | Sum of non-null values. |
| `mean(column)` | Arithmetic mean. |
| `median(column)` | Median. |
| `min(column)` | Minimum. |
| `max(column)` | Maximum. |
| `count()` | Number of rows in the group. |
| `count(column)` | Number of non-null values in that column. |

The first six rows in the table list the functions, with `count()` and `count(column)` representing two supported forms of the same function.

For example:

```
data report = sales
    .group_by(region)
    .summarize(
        revenue = sum(price * quantity),
        average_price = mean(price),
        largest_order = max(price),
        smallest_order = min(price),
        median_price = median(price),
        transactions = count(),
        customers_with_prices = count(price)
    );
```

Notice that `sum(price * quantity)` aggregates an expression rather than just a single column.

The semantic analyzer checks that aggregate expressions are used inside `summarize()`.

## 11.4 Why ordinary columns are restricted in summarize()

Consider:

```
data report = sales
    .group_by(region)
    .summarize(total = price);
```

This is rejected because `price` is not aggregated and is not a grouping key.

A group may contain multiple prices. Sweet cannot select one arbitrarily without a defined rule.

This is also invalid:

```
data report = sales
    .group_by(region)
    .summarize(total = price + 1);
```

The rule is that every column referenced in an aggregate expression must either:

- Be a grouping key when used outside an aggregate function; or
- Appear inside an aggregate function.

This is valid:

```
data report = sales
    .group_by(region)
    .summarize(total = sum(price + 1));
```

This is valid too:

```
data report = sales
    .group_by(region)
    .summarize(region_total = sum(price));
```

The output name is arbitrary, provided it does not conflict with a grouping key or another output name.

## 11.5 Group by multiple columns

```
data report = sales
    .group_by(region, customer)
    .summarize(total = sum(price));
```

This creates groups for combinations of `region` and `customer`.

If the combination is unique for every row, the resulting group sizes will be one.

## 11.6 Two-stage grouping

You can store a grouped dataset and summarize it later:

```
data grouped = sales.group_by(region);

data report = grouped.summarize(
    revenue = sum(price)
);

report.show();
```

The grouped object retains its grouping keys.

This works because `group_by()` returns a language-level `GroupedDataset` rather than a normal `Dataset`.

## 11.7 Aggregate restrictions

Your analyzer rejects nested aggregates, such as:

```
sum(mean(price))
```

It also rejects aggregate functions outside `summarize()`:

```
data result = sales.filter(sum(price) > 100);
```

The language currently has no general-purpose window-function or scalar-subquery syntax.

## 11.8 Group ordering

The backend uses:

```
group_by(..., maintain_order=True)
```

This asks Polars to preserve group encounter order.

For your sample sales data, the first occurrence of each region determines the displayed order of the grouped result.

If you require a particular business order, sort the result explicitly:

```
data report = sales
    .group_by(region)
    .summarize(revenue = sum(price))
    .sort(revenue, desc);
```

---

# 12\. Joining Datasets

Anne supports joins between datasets.

Suppose you have two files.

`orders.csv`:

```
order_id,customer_id,amount
10,1,500
11,2,250
12,4,900
13,1,75
```

`customers.csv`:

```
customer_id,name,city
1,Asha,Mumbai
2,Ben,Pune
3,Chen,Nashik
```

Load both:

```
data orders = read "orders.csv";
data customers = read "customers.csv";
```

Join them:

```
data joined = orders.join(
    customers,
    on = customer_id,
    how = "left"
);

joined.show();
```

## 12.1 Join syntax

The supported general form is:

```
data result = left_dataset.join(
    right_dataset,
    on = key,
    how = "left"
);
```

The right-hand dataset is passed as a positional dataset name.

The `on` and `how` parameters are named arguments.

## 12.2 Supported join types

Your implementation supports:

- `"inner"`
- `"left"`
- `"full"`

For example:

```
data inner = orders.join(customers, on = customer_id, how = "inner");

data left = orders.join(customers, on = customer_id, how = "left");

data full = orders.join(customers, on = customer_id, how = "full");
```

An inner join retains matching keys.

A left join preserves all rows from the left dataset, filling right-side columns with nulls when there is no match.

A full join preserves rows from both datasets.

The backend uses Polars joins with key coalescing enabled.

## 12.3 Join using multiple columns

You can use a list of column names:

```
data joined = left.join(
    right,
    on = [region, customer_id],
    how = "inner"
);
```

The list must contain plain column names, not arbitrary expressions.

## 12.4 Join-key requirements

Your analyzer checks that the key exists in both datasets.

The implementation also checks key types.

For example, joining an integer `customer_id` with a string `customer_id` is rejected when both types are known and incompatible.

The current type system is deliberately coarse-grained. It recognizes broad categories such as integer, float, string, Boolean, date, datetime, and other.

That is not a complete substitute for checking the exact underlying Polars data types.

## 12.5 Column name collisions

Suppose both datasets have an `amount` column.

The current schema builder renames the right-side non-key column:

```
amount_right
```

For example, a self-join of `orders` on `order_id` produces columns conceptually like:

```
order_id
customer_id
amount
customer_id_right
amount_right
```

Key columns are not duplicated in the output.

## 12.6 Null join keys

Your README explicitly specifies that null join keys do not match.

This is important when joining real-world datasets that contain missing identifiers.

For the precise behavior of a given Polars release, check its join semantics and configuration if null-key matching matters to your application.

---

# 13\. Dataset Actions: Display, Inspect, Explain, and Save

Most Anne methods describe transformations. Actions request results or information.

Your implementation supports seven actions.

## 13.1 show()

Display a dataset:

```
sales.show();
```

The default row limit is 20.

To display a different number of rows:

```
sales.show(5);
```

The executor collects at most `n + 1` rows. The extra row lets it indicate whether more rows were available.

The output includes a message such as:

```
(5 rows shown, more rows not shown)
```

If the dataset contains only three rows and you request five, it reports that three rows were shown.

`show()` is intended for inspecting data, not exporting an entire large dataset.

## 13.2 schema()

Display the schema:

```
sales.schema();
```

The output is conceptually:

```
column    type
customer  STRING
region    STRING
quantity  INTEGER
price     INTEGER
```

The actual inferred types depend on the input data.

Your implementation tracks a simplified Anne type system rather than displaying every Polars-specific type.

## 13.3 columns()

Display column names:

```
sales.columns();
```

Expected format:

```
[customer, region, quantity, price]
```

This is useful for quickly checking column names before writing transformations.

## 13.4 shape()

Display the number of rows and columns:

```
sales.shape();
```

Example:

```
(8 rows, 4 columns)
```

Your executor obtains the row count through a Polars query.

For a lazy dataset, determining the exact number of rows can require substantial computation. Lazy execution does not guarantee that every action is cheap.

## 13.5 describe()

Display descriptive statistics:

```
sales.describe();
```

This delegates to Polars' `describe()` method.

The resulting statistics depend on column types and the installed Polars version.

Do not assume that the output is a fixed statistical report with the same rows for every Polars release.

## 13.6 explain()

Inspect Sweet's optimized logical plan:

```
sales
    .filter(price > 100)
    .filter(quantity > 2)
    .explain();
```

This displays the logical plan maintained by Sweet.

For example, the optimized plan may resemble:

```
Filter(((price > 100) and (quantity > 2)))
  Scan(sales.csv)
```

The exact expression formatting may differ.

This is one of the most useful debugging features because it lets you see how Sweet represents your program internally.

There is an important distinction:

- `explain()` displays Sweet's logical plan.
- Polars also has its own query-plan inspection facilities.

Your current `explain()` implementation does not display the actual Polars-optimized physical execution plan.

## 13.7 save()

Export a dataset:

```
data expensive = sales.filter(price > 1000);

expensive.save("expensive.csv");
```

The file is written beneath the selected output directory.

If the output directory is:

```
results/
```

the output is:

```
results/expensive.csv
```

The supported output extensions are:

| Extension | Format |
| --- | --- |
| `.csv` | CSV |
| `.parquet` | Parquet |
| `.json` | JSON |
| `.ndjson` | Newline-delimited JSON |
| `.jsonl` | Newline-delimited JSON |

For example:

```
sales.save("sales_copy.csv");

sales.save("sales_copy.parquet");

sales.save("sales_copy.ndjson");

sales.save("sales_copy.json");
```

The current implementation materializes the complete result before writing it.

It also creates parent directories inside the output directory when needed:

```
sales.save("reports/monthly.csv");
```

### Output path safety

The semantic analyzer rejects absolute paths and paths containing `..` components.

For example:

```
sales.save("../outside.csv");
```

is rejected.

The executor independently checks that the resolved destination remains inside its output directory.

This is a useful defense-in-depth measure.

### Only explicit saves create exports

These declarations do not automatically write files:

```
data expensive = sales.filter(price > 1000);

data top = expensive.sort(price, desc).limit(5);
```

The datasets remain available in the current session.

An export happens when you explicitly call:

```
top.save("top.csv");
```

---

# 14\. A Complete Practical Tutorial

Let's combine the features into one small data-analysis workflow.

Your project already contains `examples/sales.csv`.

Its columns are:

```
customer
region
quantity
price
```

The sample contains eight rows.

## Step 1: Load the data

Create a file named `my_analysis.anne` in the `examples/` directory:

```
data sales = read "sales.csv";

sales.schema();
sales.shape();
sales.show();
```

Run:

```
sweet examples/my_analysis.anne
```

You should see the schema, row count, and sample rows.

## Step 2: Find expensive transactions

Add:

```
data expensive = sales.filter(price > 1000);

expensive.show();
```

The resulting rows should include:

- Alice, with price 1500.
- Dave, with price 2500.
- Gina, with price 1001.

The condition uses a strict comparison, so a price of exactly 1000 is excluded.

## Step 3: Calculate transaction revenue

Add:

```
data calculated = sales.derive(
    revenue = price * quantity
);

calculated.show();
```

This computes a revenue value for each row.

## Step 4: Create a regional report

Add:

```
data regional_report = calculated
    .group_by(region)
    .summarize(
        total_revenue = sum(revenue),
        average_revenue = mean(revenue),
        transaction_count = count()
    );

regional_report.show();
```

This creates one row for each region.

## Step 5: Sort the report

Add:

```
data sorted_report = regional_report.sort(
    total_revenue,
    desc
);

sorted_report.show();
```

Now the highest-revenue region appears first.

## Step 6: Export the report

Add:

```
sorted_report.save("regional_report.csv");
```

Run:

```
sweet examples/my_analysis.anne -o examples/results
```

The exported file should be:

```
examples/results/regional_report.csv
```

## Step 7: Inspect optimization

Add:

```
sales
    .filter(price > 100 * 10)
    .filter(quantity >= 2)
    .explain();
```

Sweet's optimizer can fold the constant expression:

```
100 * 10
```

into:

```
1000
```

It can also combine the adjacent filters into a single filter node.

You should therefore see a plan resembling:

```
Filter(((price > 1000) and (quantity >= 2)))
  Scan(sales.csv)
```

This small program demonstrates nearly the entire intended workflow: input, transformation, aggregation, sorting, export, and plan inspection.

---

# 15\. The Compiler Pipeline: How Anne Becomes Executable

Now let's examine the internals.

Your compiler's main entry point is `src/sweet/compiler.py`.

The overall architecture is:

```
                ANNE SOURCE CODE
                       |
                       v
                1. LEXING / PARSING
                  Lark grammar
                       |
                       v
               2. ABSTRACT SYNTAX TREE
                  AST dataclasses
                       |
                       v
               3. SEMANTIC ANALYSIS
             Names, types, schemas
                       |
                       v
               4. LOGICAL REPRESENTATION
              Expressions + plan nodes
                       |
                       v
                5. OPTIMIZATION
             Constant folding, fusion
                       |
                       v
               6. POLARS BACKEND
             Polars expression compiler
                       |
                       v
                 7. EXECUTION
              Collection and output
                       |
                       v
              DISPLAYED OR SAVED DATA
```

Let's go through each stage.

## 15.1 Stage 1: Parsing

**File:** `frontend/grammar.lark`

This file defines the grammar of Anne.

For example, the grammar specifies that a dataset declaration has the form:

```
data NAME = source ;
```

It also defines expressions, method chains, function calls, lists, and operators.

Lark reads this grammar and constructs a parser.

**File:** `frontend/parser.py`

The parser receives Anne source text:

```
data sales = read "sales.csv";

sales.filter(price > 1000).show();
```

It uses Lark to check whether the text conforms to the grammar.

If it does not, the parser raises a `SweetSyntaxError` with a source location and, where available, a helpful hint.

At this point, the parser does not execute the dataset operations.

It only determines whether the input has valid syntax.

## 15.2 Stage 2: AST construction

**Files:**

- `frontend/ast_builder.py`
- `frontend/ast_nodes.py`

The AST represents the program as structured Python objects.

For example:

```
sales.filter(price > 1000);
```

is represented conceptually as:

```
ActionStmt
└── Chain
    ├── base: NameRef("sales")
    └── calls
        └── MethodCall("filter")
            └── Arg
                └── Binary(">")
                    ├── NameRef("price")
                    └── IntLit(1000)
```

This tree captures the structure of the program.

It is more useful than manipulating raw source strings because each component has a specific meaning.

Your AST uses dataclasses such as:

```
@dataclass(frozen=True)
class Binary(Node):
    op: str
    left: Node
    right: Node
```

The `frozen=True` option prevents normal field reassignment after construction.

That makes AST nodes effectively immutable, which is a useful property for compiler code.

Another good design decision is that the AST does not depend on Lark's parse-tree objects. The parser and AST builder handle Lark; later compiler stages operate on Anne's own node classes.

## 15.3 Stage 3: Semantic analysis

**Files:**

- `semantic/analyzer.py`
- `semantic/types.py`
- `semantic/symbols.py`

Valid syntax does not guarantee a valid program.

For example:

```
data sales = read "sales.csv";

sales.filter(prcie > 1000).show();
```

This may be syntactically valid, but `prcie` is not a known column.

The semantic analyzer detects the error.

It also checks things such as:

- Whether a dataset has been defined.
- Whether a column exists.
- Whether a method is supported.
- Whether the arguments have the right form.
- Whether an expression's types are compatible.
- Whether aggregate functions appear in valid contexts.
- Whether join keys exist on both sides.
- Whether an output path is permitted.

### Symbol table

`semantic/symbols.py` implements `SymbolTable`.

It stores dataset bindings:

```
sales      -> Dataset(...)
expensive  -> Dataset(...)
report     -> Dataset(...)
```

When the analyzer encounters:

```
sales.filter(price > 1000);
```

it looks up `sales` in the symbol table.

If the name does not exist, it raises an undefined-dataset error.

### Transactional analysis

Your analyzer takes a snapshot of the symbol table before processing a program.

If analysis fails, it restores the snapshot.

This is a particularly useful feature.

Suppose a program contains:

```
data temporary = read "sales.csv";

data broken = temporary.filter(unknown_column > 10);
```

If semantic analysis fails on the second declaration, the analyzer restores the previous bindings.

For a single complete program, this helps prevent partially applied declarations from surviving a failed compilation.

In a REPL, this means successful earlier statements can remain in the session when a later input fails, provided they were committed in an earlier call to `run()`.

## 15.4 Stage 4: Dataset objects and logical IR

**Files:**

- `objects/dataset.py`
- `objects/grouped_dataset.py`
- `ir/expressions.py`
- `ir/plan_nodes.py`
- `ir/logical_plan.py`

This is where the language becomes an executable plan.

Consider:

```
data expensive = sales
    .filter(price > 1000)
    .select(customer, price);
```

The semantic analyzer creates a `Dataset` object representing the result.

That object contains two important things:

```
Dataset(
    plan=...,
    schema=...
)
```

The schema might be:

```
(
    ("customer", "STRING"),
    ("price", "INTEGER"),
)
```

The plan describes how to obtain those columns.

Conceptually:

```
Project(customer, price)
└── Filter(price > 1000)
    └── Scan(sales.csv)
```

Notice that the plan is a description of work, not the resulting table.

This distinction is fundamental to lazy execution.

### Expression IR

`ir/expressions.py` defines the expression representation:

- `Col`: a column reference.
- `Lit`: a literal value.
- `Neg`: numeric negation.
- `Not`: logical negation.
- `Bin`: a binary expression.
- `Agg`: an aggregate expression.

For example:

```
price * quantity + 10
```

becomes conceptually:

```
Bin("+")
├── Bin("*")
│   ├── Col("price")
│   └── Col("quantity")
└── Lit(10)
```

This IR is independent of Polars.

That makes it possible to analyze or optimize expressions before deciding how to execute them.

### Plan IR

`ir/plan_nodes.py` defines the logical operations:

| Node | Purpose |
| --- | --- |
| `Scan` | Read a source dataset. |
| `Filter` | Retain rows matching a predicate. |
| `Project` | Select columns. |
| `Derive` | Create or replace columns. |
| `Sort` | Sort rows. |
| `Limit` | Retain the first N rows. |
| `Tail` | Retain the last N rows. |
| `DropMissing` | Remove rows with null values. |
| `Aggregate` | Group and aggregate. |
| `Join` | Join two plans. |
| `Collected` | Mark an explicit materialization point. |

Each node is a dataclass containing the data required to describe that operation and its input plan or plans.

For example:

```
@dataclass(frozen=True)
class Filter(PlanNode):
    input: PlanNode
    predicate: object
```

The input is another plan node.

That gives Sweet a tree of operations that can be inspected, transformed, and eventually executed.

## 15.5 Stage 5: Optimization

**Directory:** `optimizer/`

The compiler invokes:

```
optimize(s.plan)
```

for each action's plan.

Your optimizer recursively processes the plan, folds expressions, removes some unnecessary filters, and fuses adjacent filters.

We'll look at the exact transformations in the next section.

## 15.6 Stage 6: Polars expression compilation

**File:** `runtime/expression_compiler.py`

Sweet's expression IR is not itself executable by Polars.

This file translates each expression node into a Polars expression.

For example:

```
Col("price")
```

becomes:

```
pl.col("price")
```

And:

```
Bin(">", Col("price"), Lit(1000))
```

becomes conceptually:

```
pl.col("price") > pl.lit(1000)
```

Arithmetic and comparison operators are dispatched through a fixed operator mapping.

Aggregate expressions map to Polars operations such as:

```
pl.col("price").sum()
```

or:

```
pl.len()
```

for `count()`.

**This is a compiler, not a Python****`eval()`****mechanism.** The source code is converted into a controlled expression representation and translated through explicit mappings.

That is easier to reason about and avoids treating Anne source as arbitrary Python code.

## 15.7 Stage 7: Backend execution

**File:** `runtime/polars_backend.py`

The backend converts logical plans into Polars `LazyFrame` objects.

For example:

```
Filter
└── Scan
```

is translated into the equivalent of:

```
pl.scan_csv(path).filter(predicate)
```

A projection becomes `select()`, a derivation becomes `with_columns()`, and an aggregation becomes `group_by().agg()`.

The backend handles the actual Polars objects.

This separation is useful because the rest of the compiler does not need to know how Polars represents a lazy query.

## 15.8 Stage 8: Execution

**File:** `runtime/executor.py`

The executor handles actions.

For example:

```
sales.show();
```

eventually calls the show action handler, which builds the lazy frame, collects a limited number of rows, and prints the resulting dataframe.

Likewise:

```
sales.save("sales.csv");
```

materializes the dataset and writes the resulting file.

The executor is responsible for presenting results to the user and converting certain low-level failures into Sweet runtime errors.

---

# 16\. Lazy Execution: One of Sweet's Most Important Features

Understanding laziness explains much of the project's architecture.

## 16.1 What is lazy execution?

In eager execution, an operation computes its result immediately.

Conceptually:

```
df = pl.read_csv("sales.csv")
filtered = df.filter(pl.col("price") > 1000)
```

The CSV is read into a dataframe before filtering.

With lazy execution:

```
lf = pl.scan_csv("sales.csv")
filtered = lf.filter(pl.col("price") > 1000)
```

Polars constructs a query plan. The actual query is executed when a result is requested.

Sweet uses this lazy approach for many operations.

## 16.2 Anne declarations are usually lazy

Consider:

```
data sales = read "sales.csv";

data expensive = sales.filter(price > 1000);

data selected = expensive.select(customer, price);
```

The intended behavior is:

1. Inspect the source schema.
2. Construct a logical scan.
3. Add a filter node.
4. Add a projection node.
5. Store the resulting dataset binding.

Sweet does not automatically collect every declared dataset.

This is tested explicitly in `test_declarations_are_lazy`.

However, schema discovery can still inspect the source, and some input formats in your implementation use eager Polars readers internally before converting the result to a lazy frame.

Therefore, the implementation is **lazy by design, but not every file-reading path is fully lazy**.

## 16.3 What triggers execution?

Your actions generally trigger execution:

```
sales.show();

sales.describe();

sales.shape();

sales.save("output.csv");
```

The `show()` action collects a limited result, while `describe()`, `shape()`, and `save()` perform their respective computations.

The `collect()` method has a different role.

It is a dataset method that explicitly materializes a dataset and introduces a `Collected` node into the plan.

For example:

```
data sales = read "sales.csv";

data cached = sales
    .filter(price > 1000)
    .collect();

cached.show();
```

This requests materialization at the `collect()` point.

Your backend caches the materialized dataframe associated with that `Collected` plan node.

## 16.4 How collect() works internally

Your implementation handles a `Collected` node approximately like this:

```
df = self._collected.get(plan)

if df is None:
    df = self.lazy(plan.input).collect()
    self._collected[plan] = df

return df.lazy()
```

The first time the collected plan is evaluated, the backend computes and stores the dataframe.

Subsequent uses of that same plan node can reuse the cached dataframe.

This can help when a costly intermediate result is reused several times.

For example:

```
data sales = read "sales.csv";

data expensive = sales
    .filter(price > 1000)
    .collect();

data a = expensive.select(customer, price);

data b = expensive.sort(price, desc);

a.show();
b.show();
```

The shared collected plan is a candidate for reuse.

### Important caching limitations

The cache is:

- Local to the backend instance.
- Keyed by the collected plan.
- Populated on demand.
- Not a persistent disk cache.
- Not automatically shared between independent CLI processes.

The cache also holds materialized data in memory.

Therefore, `collect()` should be used deliberately for expensive intermediates that are reused, rather than automatically applied to every dataset.

A further implementation detail: the executor creates a default backend for the session, so cache lifetime follows that backend's lifetime.

---

# 17\. Sweet's Optimizer

Your project implements two primary optimizations:

1. Constant folding.
2. Adjacent-filter fusion.

These optimizations operate on Sweet's own IR before execution.

Sweet does not currently implement projection pushdown or predicate pushdown itself. Those optimizations are left to Polars.

## 17.1 Constant folding

**File:** `optimizer/constant_folding.py`

Constant folding evaluates expressions that can be resolved at compile time.

For example:

```
data result = sales.filter(price > 100 * 10);
```

The expression:

```
100 * 10
```

can be replaced with:

```
1000
```

The optimized predicate becomes:

```
price > 1000
```

Other examples include:

```
1 + 2      -> 3
10 * 5     -> 50
1 < 2      -> true
-"hello"   -> not foldable
```

The last example is not a valid numeric expression under normal semantic checks. The point is that the optimizer does not blindly evaluate arbitrary expressions.

It only folds cases it explicitly supports.

## 17.2 Why constant folding is conservative

Your implementation deliberately avoids some potentially unsafe operations.

For example:

```
1 / 0
```

is not folded into a result.

Large integers that exceed the chosen 64-bit range are also not folded as ordinary integer constants.

Non-finite floating-point results are rejected as folding results.

These checks make optimization more predictable.

Your current folder also supports Boolean simplifications such as:

```
true and condition  -> condition
false and condition -> false
false or condition  -> condition
true or condition   -> true
```

It does not perform every possible algebraic simplification.

For example, the implementation does not currently fold `%` expressions, even when both operands are constants.

## 17.3 Filter fusion

**File:** `optimizer/filter_fusion.py`

Suppose you write:

```
data result = sales
    .filter(price > 100)
    .filter(quantity > 2);
```

The original plan is:

```
Filter(quantity > 2)
└── Filter(price > 100)
    └── Scan(sales.csv)
```

Sweet can rewrite it as:

```
Filter((price > 100) and (quantity > 2))
└── Scan(sales.csv)
```

This reduces the number of Sweet filter nodes.

It is important to understand that filter fusion does not mean Sweet independently proves that every execution will become faster. The practical benefit depends on the backend and its query optimizer.

## 17.4 Removing filters that are always true

The optimizer also removes a filter whose predicate folds to `true`.

For example:

```
data result = sales.filter(100 < 200);
```

The condition is constant and true.

The optimizer can replace the filtered plan with its input.

This avoids performing an unnecessary filter operation.

A constant-false predicate is not handled by an equivalent dedicated empty-plan rewrite in your current optimizer.

## 17.5 Optimizations delegated to Polars

Sweet's own optimizer does not implement:

- Predicate pushdown.
- Projection pushdown.
- Join reordering.
- Cost-based optimization.
- A complete physical execution planner.

Polars may perform several of its own optimizations on the lazy query generated by Sweet.

For example, if a program selects only two columns, Polars may be able to avoid reading unnecessary columns from a compatible source format.

But that behavior belongs to Polars, not to Sweet's custom optimizer.

This separation is reasonable for a small compiler: Sweet implements a few language-specific rewrites and relies on Polars for dataframe execution planning.

---

# 18\. The Type System

Your implementation includes a small static type system.

**File:** `semantic/types.py`

It defines these principal types:

| Anne type | Meaning |
| --- | --- |
| `INTEGER` | Integer values. |
| `FLOAT` | Floating-point or recognized decimal values. |
| `STRING` | Text values. |
| `BOOLEAN` | True/false values. |
| `DATE` | Date values. |
| `DATETIME` | Date-and-time values. |
| `OTHER` | Types not mapped to one of the categories above. |

The type system serves two main purposes:

1. It catches certain invalid expressions before execution.
2. It constructs the output schema for transformed datasets.

## 18.1 Numeric expressions

These are supported:

```
data result = sales.derive(
    sum_value = price + quantity,
    difference = price - quantity,
    product = price * quantity,
    quotient = price / quantity
);
```

Integer arithmetic generally retains `INTEGER` when appropriate, while division produces `FLOAT`.

Mixing integers and floating-point values produces a floating-point result.

## 18.2 String expressions

Two strings can be concatenated:

```
data result = sales.derive(
    label = customer + " - " + region
);
```

String concatenation is supported by both the semantic checker and expression compiler.

## 18.3 Boolean expressions

Conditions can be used in filters and derived columns:

```
data result = sales.derive(
    expensive = price > 1000
);
```

The resulting column has Boolean type.

The type checker also rejects filters that do not produce a Boolean-compatible expression:

```
data result = sales.filter(price);
```

A numeric column is not a valid filter condition in Anne.

## 18.4 Type inference

When a dataset is loaded, the analyzer obtains its schema from Polars.

The `from_polars()` function maps Polars types to Anne types.

When a new column is derived, the analyzer infers its type from the expression.

For example:

```
data result = sales.derive(
    revenue = price * quantity,
    expensive = price > 1000,
    label = customer + "!"
);
```

The resulting schema should classify:

- `revenue` as numeric.
- `expensive` as Boolean.
- `label` as string.

This schema is used during subsequent semantic checks.

## 18.5 Limitations of type inference

The type system is intentionally simplified.

It does not preserve every distinction in Polars' type system.

For example, several distinct numeric types may all become `INTEGER`.

Some unsupported or unrecognized types become `OTHER`.

The implementation also does not provide a general-purpose type-casting syntax, explicit type declarations, user-defined types, or a comprehensive nullability system.

These are reasonable future development opportunities if you want Anne to handle more complicated datasets safely.

---

# 19\. Error Handling and Debugging

Sweet has separate exception classes for syntax, semantic, and runtime errors.

**File:** `diagnostics/errors.py`

The main classes are:

- `SweetSyntaxError`
- `SweetSemanticError`
- `SweetRuntimeError`

All inherit from `SweetError`.

## 19.1 Syntax errors

Consider:

```
data sales = read "sales.csv"
```

The missing semicolon causes a syntax error.

The parser attempts to provide:

- The unexpected token.
- A line and column.
- An indication of expected syntax.
- A suggestion when it can infer one.

## 19.2 Semantic errors

Example:

```
data sales = read "sales.csv";

data expensive = sales.filter(prcie > 1000);
```

The unknown column is a semantic error.

Your `unknown_column()` helper uses `difflib.get_close_matches()` to suggest likely alternatives.

The output can resemble:

```
error: unknown column 'prcie'
help: did you mean 'price'?
```

Other semantic errors include:

- Undefined dataset.
- Duplicate dataset binding.
- Unknown method.
- Unsupported file format.
- Invalid argument count.
- Incompatible expression types.
- Invalid grouping expressions.
- Invalid join configuration.

## 19.3 Runtime errors

Runtime errors occur when an operation fails during execution.

Examples include:

- An invalid file operation.
- A Polars execution failure.
- A failed export.

Your executor catches certain Polars and operating-system exceptions and converts them to `SweetRuntimeError`.

Not every possible exception is currently normalized, so some edge cases may still expose lower-level Python exceptions.

## 19.4 Source locations

Your AST nodes retain line, column, and source-span information.

Semantic errors can attach to the relevant AST node.

The CLI then uses:

```
e.render(source, filename)
```

to produce a diagnostic with a source excerpt and caret marker.

This is a good foundation for future tooling, including IDE integration.

## 19.5 A practical debugging workflow

When a program fails, use this sequence:

1. Check the line and column in the error.
2. Verify dataset names.
3. Check column names using `schema()` or `columns()`.
4. Simplify the expression that caused the problem.
5. Use `--check` to identify semantic errors without executing actions.
6. Use `explain()` to inspect the optimized plan.
7. If the problem occurs only during execution, inspect the relevant backend or I/O code.

For example:

```
data sales = read "sales.csv";

sales.columns();

sales.schema();
```

This can help diagnose unknown-column errors before you construct a larger transformation.

---

# 20\. Testing the Compiler

Your test suite is organized into four major areas.

Run all tests using:

```
pytest -q
```

Or:

```
python -m pytest -q
```

## 20.1 Frontend tests

**File:** `tests/test_frontend.py`

These tests check:

- Parsing declarations and method chains.
- AST construction.
- Separation between AST nodes and Lark objects.
- Named versus positional arguments.
- Operator precedence.
- Reader options.
- Syntax error locations.
- Invalid characters.

These tests protect the grammar and AST builder.

If you change `grammar.lark`, run these tests first.

## 20.2 Semantic tests

**File:** `tests/test_semantics.py`

These test:

- Unknown columns and method suggestions.
- Duplicate dataset bindings.
- Undefined datasets.
- Rollback after a failed program.
- Grouping restrictions.
- Aggregate placement.
- Type errors.
- Join errors.
- Save path validation.
- Reader option validation.
- Source-aware diagnostics.

These tests are especially valuable when adding language features.

## 20.3 Optimizer tests

**File:** `tests/test_optimizer.py`

These verify:

- Constant folding.
- Conservative handling of unsafe expressions.
- Boolean simplification.
- Filter fusion.
- Logical-plan output.
- Agreement between optimized and unoptimized execution for a test case.

The last test is particularly important.

An optimizer is only correct if its transformations preserve program behavior.

For more comprehensive validation, you would want to compare optimized and unoptimized execution across many generated expressions and datasets.

## 20.4 End-to-end tests

**File:** `tests/test_end_to_end.py`

These exercise the language as a whole.

They cover:

- Inspection actions.
- Chained transformations.
- Grouping and aggregation.
- Joins.
- Exports in multiple formats.
- Path safety.
- Reusing dataset bindings.
- Lazy declarations.
- `collect()` caching.
- Schema consistency.
- Reader options.
- Excel input.
- CLI behavior.
- REPL behavior.

These tests are integration tests: they validate interactions between multiple compiler components.

## 20.5 What to do if tests fail

If the installation reaches the test stage and stops, start by running:

```
cd anne-sweet
source .venv/bin/activate
python -m pytest -q
```

For more detail:

```
python -m pytest -vv
```

To isolate a category:

```
python -m pytest tests/test_frontend.py -q
```

```
python -m pytest tests/test_semantics.py -q
```

```
python -m pytest tests/test_optimizer.py -q
```

```
python -m pytest tests/test_end_to_end.py -q
```

Because the setup script uses `set -e`, a failing test suite stops the script before the demo and final PATH configuration.

That is useful for catching problems early, but it also means a partially installed project may exist after a failed setup.

---

# 21\. Important Limitations and Code Issues to Know

Your project has a good modular foundation, but there are some differences between what the language is designed to support and what the implementation currently guarantees.

The following points are worth understanding before using Sweet for important data-processing work.

## 21.1 `--check` is not completely static

Although `--check` avoids executing actions, the analyzer calls `schema_of()` while processing `read`.

That means:

```
sweet program.anne --check
```

may still open input files and inspect their schemas.

Additionally, some readers, notably the current JSON and Excel paths, use eager Polars readers internally.

**Possible improvement:** separate schema discovery from data materialization, and clearly document which input formats require reading data during compilation.

## 21.2 The schema type system is simplified

Sweet maps Polars types into broad categories.

This is useful for catching common errors, but it is not full type equivalence.

For example, two distinct integer types may both be represented as `INTEGER`.

That means some incompatible underlying types may pass semantic checks and fail later during execution.

**Possible improvement:** preserve the original Polars dtype alongside the Anne type, and use the exact dtype when validating joins and operations.

## 21.3 Missing-value handling is limited

The current implementation uses:

```
child.drop_nulls(...)
```

It does not treat NaN as null.

**Possible improvement:** add a separate method such as:

```
data clean = sales.drop_nan(price);
```

Alternatively, extend the missing-value API to let users specify which kinds of missing values should be removed.

## 21.4 No explicit type conversion

The language does not currently provide methods like:

```
# Illustrative future syntax, not currently supported.
data typed = raw.cast(price = "FLOAT");
```

Consequently, you cannot use a built-in Anne casting operation to convert a text column into a numeric column.

For datasets with inconsistent inferred types, this is a significant limitation.

A future `cast()` method could support a defined set of target types and report invalid conversions clearly.

## 21.5 No general-purpose expression functions

Your expression language supports a limited set of arithmetic, comparison, and aggregation functions.

It does not currently provide a general-purpose set of functions for:

- String transformations.
- Date arithmetic.
- Date parsing.
- Regular expressions.
- Conditional expressions such as `if` or `when`.
- Null-handling functions.
- Type casts.
- Window functions.

Polars supports many of these operations, but Anne cannot automatically access every Polars operation.

To expose a new operation, you would generally need to update the grammar if necessary, the expression IR, semantic analysis, and expression compiler.

## 21.6 Constant folding does not cover every operator

The current optimizer folds a subset of constant expressions.

For example, it deliberately leaves remainder expressions such as:

```
7 % 3
```

unfolded.

That is not necessarily a correctness bug. It is simply an optimization that has not been implemented.

**Possible improvement:** add folding rules incrementally, with explicit handling for division by zero, overflow, types, and exceptions.

## 21.7 Filter fusion is a simple rewrite

Sweet fuses adjacent filters.

It does not implement a sophisticated cost-based optimizer.

For example, it does not independently decide which of several joins should execute first based on estimated data sizes.

Those are possible future compiler features, although Polars already handles many execution optimizations for the supported query plans.

## 21.8 The output format is not streamed by Sweet

The `save()` implementation collects the complete dataframe before writing it.

This can consume substantial memory for large results.

The CSV and Parquet writers may support more advanced streaming strategies through Polars, but Sweet does not currently expose a general streaming-export mechanism.

**Possible improvement:** introduce a carefully designed streaming execution path and validate which transformations can safely participate in it.

## 21.9 `collect()` is an in-memory cache

Explicit materialization is useful, but it is not a persistent cache.

It does not automatically share results across separate runs of the CLI.

It also does not guarantee that all intermediate data is released promptly while a session remains alive.

For long-running REPL sessions, consider providing a way to clear cached results.

## 21.10 Runtime errors are not all normalized

The executor catches Polars errors and operating-system errors around action execution.

However, certain exceptions may arise outside those handlers.

For example, invalid internal IR, unexpected exceptions from a third-party library, or malformed externally constructed action objects could expose lower-level Python errors.

**Possible improvement:** add focused exception handling around the relevant boundaries while preserving useful error messages and avoiding the concealment of programming bugs.

## 21.11 Source locations are not consistently attached to every error

Your AST stores source locations, and the analyzer frequently attaches them through `_at()`.

This is a strong foundation.

However, not every error-producing code path is guaranteed to have the most specific possible location.

For example, type errors arising from nested expressions may sometimes point to the surrounding method call rather than the precise operator.

**Possible improvement:** carry source locations through the expression IR or maintain a source map from IR nodes back to AST nodes.

## 21.12 The optimizer should be tested more broadly

Your existing optimizer tests include useful examples, but a compiler optimizer deserves more systematic validation.

A valuable future test strategy would be:

1. Generate a dataset with a variety of types and null values.
2. Construct many valid Anne expressions.
3. Run the resulting plans with optimization enabled and disabled.
4. Compare their results, including schemas and row order where relevant.
5. Include edge cases involving overflow, nulls, NaNs, and floating-point arithmetic.

This helps catch transformations that work for simple examples but fail under less common data conditions.

---

# 22\. How to Extend Sweet with New Features

Suppose you want to add a feature such as `distinct()` to remove duplicate rows.

The existing architecture gives you a reasonably clear implementation path.

## Step 1: Decide the language syntax

For example:

```
data unique_customers = sales.select(customer).distinct();
```

This is a proposed extension, not currently supported by the supplied implementation.

Decide whether `distinct()` should remove duplicate rows across all columns or accept a list of columns.

For an initial implementation, removing duplicate rows across all columns is simpler.

## Step 2: Add a logical plan node

In `ir/plan_nodes.py`, add something like:

```
@dataclass(frozen=True)
class Distinct(PlanNode):
    input: PlanNode
```

This represents the operation without depending on Polars.

## Step 3: Add the dataset method

In `objects/dataset.py`:

```
def distinct(self):
    return Dataset(
        P.Distinct(self.plan),
        self.schema,
    )
```

The method preserves the schema while adding a plan node.

## Step 4: Register the method

In `semantic/analyzer.py`, add `"distinct"` to:

```
DATASET_METHODS
```

Then implement the corresponding dispatch method:

```
def _m_distinct(self, ds, call):
    self._positional(call, 0, 0, "distinct()")
    return ds.distinct()
```

This validates the arguments and invokes the dataset abstraction.

## Step 5: Add backend execution

In `runtime/polars_backend.py`, handle the new plan node:

```
if isinstance(plan, P.Distinct):
    return child.unique(maintain_order=True)
```

Here, `child` is the lazy frame produced from the input plan.

Check the supported API and behavior for your installed Polars version.

## Step 6: Add plan formatting

In `ir/logical_plan.py`, add a representation such as:

```
if isinstance(n, P.Distinct):
    return "Distinct"
```

This makes the operation visible in `explain()`.

## Step 7: Add tests

At minimum, test:

- Removing duplicate rows.
- Preserving the schema.
- Correct interaction with filtering and sorting.
- Correct optimized-plan formatting.
- Runtime behavior on empty datasets.
- Null-value behavior.
- Error handling.

The important lesson is that a language feature often crosses several compiler layers. Keeping those layers separate makes changes easier to reason about.

---

# 23\. Recommended Improvements to the Language

If your goal is to turn Sweet into a practical dataset language, I would prioritize features in the following order.

## Priority 1: Data cleaning and schema control

Add:

- `cast()`
- `rename()`
- `distinct()`
- `fill_missing()`
- `drop_missing()` improvements
- Explicit column selection and renaming in joins.

These features make everyday data-cleaning workflows much easier.

## Priority 2: Conditional expressions

A useful extension would be a conditional expression.

For example, a possible future syntax could be:

```
data categorized = sales.derive(
    category = when(price > 1000, "expensive", "affordable")
);
```

The exact syntax would need to be defined in the grammar and semantic analyzer.

The expression compiler would translate it into an appropriate Polars conditional expression.

This would make it possible to categorize rows without requiring several separate datasets.

## Priority 3: String and date functions

Useful functions could include:

- `lower()`
- `upper()`
- `trim()`
- `contains()`
- `starts_with()`
- Date parsing and formatting.
- Date extraction.
- Date arithmetic.

These operations are particularly valuable when working with real-world CSV and Excel files.

## Priority 4: More robust type handling

Improve:

- Exact dtype tracking.
- Type conversions.
- Nullability analysis.
- Date and datetime inference.
- Join compatibility checks.
- Diagnostics for invalid arithmetic.

This would help catch errors before expensive execution begins.

## Priority 5: Better execution and caching

Consider:

- More flexible materialization.
- Streaming exports where supported.
- Cache management.
- Polars plan inspection.
- Execution timing.
- Memory usage diagnostics.

These features become increasingly important as datasets grow.

## Priority 6: Language tooling

Potential additions include:

- Syntax highlighting.
- Editor support.
- A language server.
- Better completion suggestions.
- A formatter.
- A language reference.
- A standard library.
- Versioned language specifications.

Your current AST and diagnostics architecture provides a starting point for this work.

---

# 24\. Command Reference: Quick Cheat Sheet

Here is a compact reference you can keep beside you while working with Anne.

## Command-line commands

| Command | Purpose |
| --- | --- |
| `sweet --version` | Display the installed version. |
| `sweet --help` | Show command-line help. |
| `sweet program.anne` | Execute a program. |
| `sweet program.anne --check` | Parse and analyze without executing actions. |
| `sweet program.anne -o output` | Set the export directory. |
| `sweet` | Start the REPL. |
| `pytest -q` | Run the test suite. |

## Dataset operations

| Operation | Example |
| --- | --- |
| Read | `data x = read "data.csv";` |
| Filter | `x.filter(price > 100);` |
| Select | `x.select(name, price);` |
| Derive | `x.derive(total = price * quantity);` |
| Sort ascending | `x.sort(price);` |
| Sort descending | `x.sort(price, desc);` |
| First N rows | `x.limit(10);` |
| First N rows, alias | `x.head(10);` |
| Last N rows | `x.tail(10);` |
| Remove nulls | `x.drop_missing();` |
| Group | `x.group_by(region);` |
| Aggregate | `x.group_by(region).summarize(total = sum(price));` |
| Join | `x.join(y, on = id, how = "left");` |
| Materialize | `x.collect();` |

These operations can be chained to construct more complex datasets.

## Dataset actions

| Action | Example |
| --- | --- |
| Display rows | `x.show();` |
| Display five rows | `x.show(5);` |
| Display schema | `x.schema();` |
| Display column names | `x.columns();` |
| Display dimensions | `x.shape();` |
| Display statistics | `x.describe();` |
| Display logical plan | `x.explain();` |
| Export results | `x.save("result.csv");` |

## Operators

| Category | Operators |
| --- | --- |
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Logical | `and`, `or`, `not` |

---

# 25\. Five Complete Examples to Practice

These examples use the sample data supplied by your setup script.

Run them from the project root, using the `examples/` directory for your `.anne` files.

## Example 1: Basic exploration

```
data sales = read "sales.csv";

sales.show(5);

sales.columns();

sales.schema();

sales.shape();

sales.describe();
```

Learn how to load a dataset and inspect its structure.

## Example 2: Filtering and calculating

```
data sales = read "sales.csv";

data result = sales
    .filter(price > 1000)
    .derive(revenue = price * quantity)
    .select(customer, region, price, revenue)
    .sort(revenue, desc);

result.show();
```

Learn how to filter rows, calculate a column, select columns, and sort.

## Example 3: Regional analysis

```
data sales = read "sales.csv";

data report = sales
    .derive(revenue = price * quantity)
    .group_by(region)
    .summarize(
        revenue = sum(revenue),
        average_price = mean(price),
        transaction_count = count()
    )
    .sort(revenue, desc);

report.show();

report.save("regional_report.csv");
```

Learn grouping, aggregation, and exporting.

## Example 4: Joining files

```
data orders = read "orders.csv";

data customers = read "customers.csv";

data result = orders
    .join(customers, on = customer_id, how = "left")
    .select(order_id, customer_id, name, city, amount)
    .sort(order_id);

result.show();

result.save("joined_orders.parquet");
```

Learn how to combine datasets.

## Example 5: Inspecting optimization

```
data sales = read "sales.csv";

data result = sales
    .filter(price > 100 * 10)
    .filter(quantity > 1)
    .select(customer, price, quantity)
    .sort(price, desc);

result.explain();

result.show();
```

Learn how Sweet builds and optimizes logical plans.

Save each example to a separate `.anne` file, then run it:

```
sweet examples/basic.anne -o results
```

To validate the program before executing it:

```
sweet examples/basic.anne --check
```

---

# 26\. How I Recommend Learning the Internals

If you want to understand Sweet as a compiler project rather than simply use it, follow this learning sequence.

### Phase 1: Understand the language

Start with:

```
src/sweet/frontend/grammar.lark
src/sweet/frontend/ast_nodes.py
src/sweet/frontend/ast_builder.py
src/sweet/frontend/parser.py
```

Your goal is to understand how a line such as:

```
sales.filter(price > 1000);
```

becomes an AST.

Read the grammar, parse a few examples, and inspect the AST nodes.

### Phase 2: Understand semantic analysis

Read:

```
src/sweet/semantic/analyzer.py
src/sweet/semantic/types.py
src/sweet/semantic/symbols.py
```

Your goal is to understand how Sweet resolves dataset names, checks column names, infers expression types, and rejects invalid programs.

Practice by introducing deliberate errors:

```
data sales = read "sales.csv";

data result = sales.filter(prcie > 1000);
```

Then trace how the error is generated.

### Phase 3: Understand logical plans

Read:

```
src/sweet/objects/dataset.py
src/sweet/objects/grouped_dataset.py
src/sweet/ir/expressions.py
src/sweet/ir/plan_nodes.py
src/sweet/ir/logical_plan.py
```

Your goal is to understand how dataset operations become nodes in a plan.

Use `explain()` to connect the code to the output.

### Phase 4: Understand optimization

Read:

```
src/sweet/optimizer/constant_folding.py
src/sweet/optimizer/filter_fusion.py
src/sweet/optimizer/optimizer.py
```

Your goal is to understand how the plan changes before execution.

Try adding an optimization, then write a test that compares the optimized and unoptimized results.

### Phase 5: Understand execution

Read:

```
src/sweet/runtime/expression_compiler.py
src/sweet/runtime/polars_backend.py
src/sweet/runtime/io.py
src/sweet/runtime/executor.py
```

Your goal is to understand how a logical plan becomes Polars operations and how those operations produce actual results.

### Phase 6: Understand the application

Finally, read:

```
src/sweet/compiler.py
src/sweet/cli.py
src/sweet/repl.py
```

These files connect the components into a usable application.

By the end, you should understand the complete flow from source code to output.

---

# 27\. Final Assessment of Your Project

Your Sweet/Anne implementation already has several valuable characteristics.

- **A real compiler pipeline:** parsing, AST construction, semantic analysis, IR, optimization, and execution are separate stages.
- **An independent language representation:** the AST and logical IR do not depend directly on Polars.
- **A useful dataset abstraction:** transformations return new dataset objects rather than immediately producing dataframes.
- **Lazy execution:** many operations build plans instead of eagerly processing the entire dataset.
- **Basic optimization:** constant folding and filter fusion simplify plans.
- **Semantic diagnostics:** the analyzer checks names, types, method calls, and argument structure.
- **Multiple data formats:** CSV, TSV, Parquet, JSON, NDJSON, and Excel inputs are supported through the declared readers.
- **Explicit exports:** files are written through `save()` rather than automatically after every transformation.
- **A shared CLI and REPL pipeline:** interactive and batch execution use the same compiler.
- **Automated tests:** the project includes frontend, semantic, optimizer, and end-to-end coverage.

The main limitations are the relatively small expression language, simplified type system, lack of general-purpose casting and cleaning functions, limited custom optimization, and the memory implications of materializing complete datasets for exports.

Those are manageable limitations for a small compiler project.

## The most important concept to remember

Think of Sweet as three systems working together:

1. **Anne is the language:** you describe dataset operations.
2. **Sweet is the compiler:** it parses your program, checks it, constructs a plan, and optimizes that plan.
3. **Polars is the execution engine:** it performs the actual dataframe computations.

For example:

```
data sales = read "sales.csv";

data report = sales
    .filter(price > 100)
    .derive(revenue = price * quantity)
    .group_by(region)
    .summarize(total = sum(revenue))
    .sort(total, desc);

report.show();

report.save("report.csv");
```

The Anne code describes the workflow. Sweet converts it into a logical plan. Polars executes that plan when the result is requested.

**My recommendation:** first get the setup script to complete successfully, then work through the five practical examples. After that, trace one example through the parser, analyzer, IR, optimizer, and backend. That will give you both the practical skills to use Anne and the architectural understanding needed to develop Sweet further.
