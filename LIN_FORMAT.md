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

## Expanding Handviewer links

When asked to expand the shortened BBO links in a `link.txt` file:

1. Resolve each shortened URL by following its redirects to the final
   `www.bridgebase.com/tools/handviewer.html` URL.
2. Keep the existing header and all shortened URLs unchanged.
3. After the original link list, add a blank line, the heading `展開URL`, and
   one expanded URL per board, using the same `番号番: URL` format and board
   order as the original list.
4. Write the expanded links into that same `link.txt`. Do not replace the
   shortened links or create a separate output file.
5. Verify that the expanded-link count matches the original count and that the
   original shortened URLs remain present.

## Merging feature branches

When asked to create a PR and merge a feature branch:

1. Create the PR against `development` and merge it.
2. After the merge succeeds, switch to `development`, pull the latest changes,
   and delete both the local and remote feature branch.
3. Keep the branch if the merge fails.
