| project | result | turns (build+review[+extra]) | notes |
|---|---|---|---|
| artisan-coffee | FAIL | 5+5+2 | PASS index.html exists (6348 chars); FAIL localStorage; PASS accordion; FAIL visible words > 1200 (325); FAIL sections >= 9 (8); FAIL inline SVG >= 4 (1); PASS no lorem ipsum; FAIL CSS custom properties; FAIL @media queries; FAIL :focus styles; FAIL interactions >= 3 |
| taskman | PASS | 99+30 | PASS taskman.py exists; PASS test_taskman.py exists; PASS unittest green (Ran 10 tests); PASS >=10 tests; PASS tests use subprocess; PASS subcommands in --help |
| viper | FAIL | 3+17+13 | PASS index.html exists (8338 chars); PASS requestAnimationFrame; PASS has <canvas; PASS has localStorage; PASS has pause; FAIL has restart |