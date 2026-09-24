# LIN format notes

Use the working `board1.lin` structure for generated board files:

```text
pn|South,West,North,East|st||md|<dealer><South hand>,<West hand>,<North hand>,<East hand>|sv|<vulnerability>|rh||ah|Board <number>|
```

Rules:

- Keep the metadata prefix exactly as `pn|South,West,North,East|st||`.
- The `md` tag starts with the BBO dealer number: `1=South`, `2=West`, `3=North`, `4=East`. Therefore boards 1, 5, 9, ... use `3`; boards 2, 6, 10, ... use `4`; boards 3, 7, 11, ... use `1`; boards 4, 8, 12, ... use `2`.
- Store hands in this exact order: South, West, North, East.
- Separate the four hands with commas.
- Use `S`, `H`, `D`, and `C` for suits.
- Convert rank `10` to `T`.
- Preserve `sv|o|`, `sv|n|`, `sv|e|`, or `sv|b|` for vulnerability.
- End with `rh||ah|Board <number>|`.
- Add a trailing newline.
- File names are `#<board number>.lin`.
- Use ASCII English for folder names to avoid BBO character encoding issues.
- Use the folder pattern `YYYY-MM-DD - <English match name> Session <number>`.

## Generation workflow

Run `generate_lin.py` with the result-page URL and the English match directory:

```text
python3 generate_lin.py --url <result-page-url> --output-dir <match-directory>
```

The script validates every generated deal immediately. A failed board is fetched
again until it passes or three attempts have been made. After three failures,
the board is left out of the upload set and its Japanese error reason is added
to `error.txt`.
