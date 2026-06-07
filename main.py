from playwright.sync_api import sync_playwright
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def select_subject(page, abbreviation, number):
    page.locator('button[aria-label="subject"]').click()

    page.locator(
        f'input[data-name="selectItemsubject[]"][value="{abbreviation}"]'
    ).check()

    page.fill("#courseNumberFilter", number)


def get_next_term(page):
    options = page.locator("#termFilter option")

    terms = []

    for i in range(options.count()):
        opt = options.nth(i)
        value = opt.get_attribute("value")
        text = opt.inner_text().strip()

        if not value:
            continue

        terms.append((int(value), value, text))

    terms.sort(key=lambda x: x[0])

    today = datetime.today()
    month = today.month
    year = today.year

    suffix = "10" if 8 <= month <= 12 else "15" if month <= 2 else "20" if month <= 5 else "30"
    guess = str(year) + suffix

    values = [t[1] for t in terms]

    if guess in values:
        idx = values.index(guess)
        if idx + 1 < len(values):
            return terms[idx + 1][1], terms[idx + 1][2]

    for t in terms:
        if int(t[1]) > int(guess):
            return t[1], t[2]

    return terms[-1][1], terms[-1][2]


def get_open_courses(page, name):
    page.wait_for_selector("#resultsTable tbody tr")

    rows = page.locator("#resultsTable tbody tr")
    count = rows.count()

    table = Table(title="Open Courses", box=box.ROUNDED)
    table.add_column("Course", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("CRN", style="magenta")
    table.add_column("Seats", style="green")

    found = 0

    for i in range(count):
        row = rows.nth(i)

        subject = row.locator("td").nth(0).inner_text().strip()
        number = row.locator("td").nth(1).inner_text().strip()
        title = row.locator("td").nth(2).inner_text().strip()
        section = row.locator("td").nth(3).inner_text().strip()
        crn = row.locator("td").nth(4).inner_text().strip()
        seats = row.locator("td").nth(7).inner_text().split()[0].strip()

        try:
            enrolled, capacity = seats.split("/")
            enrolled = int(enrolled)
            capacity = int(capacity)
        except:
            continue

        if capacity != 0 and enrolled >= capacity:
            continue

        table.add_row(
            f"{name} {number}-{section}",
            title,
            crn,
            seats
        )
        found += 1

    if found == 0:
        console.print("[red]No open courses found[/red]")
    else:
        console.print(table)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    console.print(Panel.fit("📚 Course Finder", style="bold blue"))

    name = console.input("[bold yellow]Enter course '[SUBJECT] [NUMBER]': [/bold yellow]")

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[bold cyan]{task.description}"),
        console=console,
    ) as progress:

        steps = [
            "Opening website",
            "Setting campus",
            "Selecting term",
            "Selecting course",
            "Searching",
            "Loading results"
        ]

        task = progress.add_task("Starting...", total=len(steps))

        # 1
        progress.update(task, description=steps[0])
        page.goto("https://www.apps.miamioh.edu/courselist/")
        progress.advance(task)

        # 2
        progress.update(task, description=steps[1])
        page.locator('button[aria-label="campus"]').click()
        page.locator('input[data-name="selectItemcampusFilter[]"][value="O"]').check()
        progress.advance(task)

        # 3
        progress.update(task, description=steps[2])
        term_value, term_label = get_next_term(page)
        console.print(f"[green]Using term:[/green] {term_label}")
        page.locator("#termFilter").select_option(term_value)
        progress.advance(task)

        # 4
        progress.update(task, description=steps[3])
        course = name.split(" ")
        select_subject(page, course[0], course[1])
        progress.advance(task)

        # 5
        progress.update(task, description=steps[4])
        page.locator("#courseSearch").click()
        progress.advance(task)

        # 6
        progress.update(task, description=steps[5])
        page.wait_for_timeout(2000)
        progress.advance(task)

    console.print("\n[bold green]Results loaded![/bold green]\n")

    get_open_courses(page, name.split(" ")[0])

    browser.close()