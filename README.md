# Курсовая работа - построение расписаний

Программа на C++ для построения расписаний зависимых работ на нескольких процессорах с учётом задержек передачи данных.

В проекте две версии:
- `coursework_kret` - старая программа, принимает формат 1 (`.in`).
- `my_coursework` - модифицированная программа, принимает формат 2 (RS2) с отдельной матрицей задержек. Также есть поддержка формата 1.

## Входные данные

- **Формат 1:** один `.in`-файл с длительностями работ, зависимостями и матрицей задержек.
- **Формат 2:** граф RS2 (`node size children`) и отдельный файл с квадратной матрицей задержек.

Число процессоров определяется размером матрицы.

## Алгоритмы

Поддерживаемые эвристики: `misf`, `edfbase`, `edffollow`, `edfb_misf`, `edff_misf`, `est`, `eft`.

Эвристика выбирается через `--command`.

## Сборка

Из корня проекта:

```bash
cmake -S coursework_kret/algo -B coursework_kret/algo/build -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build coursework_kret/algo/build -j4

cmake -S my_coursework/algo -B my_coursework/algo/build -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build my_coursework/algo/build -j4
```

Необходимы: CMake, компилятор C++ и Boost.

## Запуск

**Новая программа (RS2):**

```bash
cd my_coursework/algo
make run
```

**Старая программа (`.in`):**

```bash
cd coursework_kret/algo
build/sched --input ../layer_class_1_based_on_1/5_500.in --output ../outputdir/output.json --conf config.toml --command misf --random 1234
```

Результаты сохраняются в JSON и содержат расписание работ по процессорам.

## Проверка

Из папки `coursework_kret/algo`:

```bash
python3 tests/format_compare/test_schedules.py --original build/sched --modified ../../my_coursework/algo/build/sched
```

На 22 подготовленных графах расписания двух программ совпадают: **22/22 PASS**.

## Конвертация форматов

Для сравнения программ используется один граф RS2 и одна матрица задержек.

Сначала генерируем матрицу (пример для 4 процессоров с одинаковой задержкой 7):

```bash
python3 scripts/generate_delay_matrix.py --processors 4 --delay 7 --output /tmp/delays.txt
```

Затем преобразуем RS2 в формат 1, используя ту же матрицу:

```bash
python3 coursework_kret/algo/tests/format_compare/convert_to_format1.py --input tests/format_compare_graphs/triang_small/triang_4.txt --matrix /tmp/delays.txt --output /tmp/graph.in
```

Полученный `.in` передаётся старой программе. Новая программа получает исходный RS2-граф и ту же матрицу напрямую.

Конвертация выполняется отдельно от запуска программ и сравнения расписаний.

## Сравнение программ

Сравнение на одном графе:

```bash
python3 scripts/compare_schedules.py --graph triang_small/triang_4 --processors 4 --delay 7
```

Проверка всех 22 графов:

```bash
python3 scripts/compare_all.py
```

Скрипты автоматически генерируют матрицы задержек, преобразуют входные данные, запускают обе программы и сравнивают расписания.

Результаты и логи сохраняются в `/tmp/coursework_compare` и `/tmp/coursework_compare_all`.

## Визуализация

Для диаграмм Ганта требуется `matplotlib` (`sudo apt install python3-matplotlib`).

После запуска `compare_schedules.py` можно построить два изображения:

```bash
D=/tmp/coursework_compare/triang_small/triang_4

python3 coursework_kret/algo/tests/format_compare/visualize_graphs.py --rs2 coursework_kret/algo/tests/format_compare_graphs/triang_small/triang_4.txt --format1 "$D/graph.in" --output "$D/graphs.svg"

python3 scripts/visualize_schedules.py --new "$D/normalized_new.json" --old "$D/normalized_old.json" --output "$D/schedules.svg"
```

`graphs.svg` - два графа (RS2 слева, `.in` справа).

`schedules.svg` - две диаграммы построенных расписаний (новая программа сверху, старая снизу). Цвета обозначают работы, штриховка - простои.

## Проверка различных эвристик

Автоматическое сравнение двух программ для 7 эвристик и задержек 2 и 7:

```bash
python3 scripts/compare_heuristics.py
```

Проверка конкретного графа с 16 процессорами:

```bash
python3 scripts/compare_heuristics.py --graph triang/triadag10_0 --processors 16
```

Проведены две серии проверок совпадения расписаний:

- **308 сравнений:** 22 графа разных типов (`layered`, `rand`, `triang`, `triang_small`), 7 эвристик (`misf`, `eft`, `est`, `edfbase`, `edfb_misf`, `edffollow`, `edff_misf`), 2–5 процессоров и задержки 2 и 7. Для каждого графа использовалось заданное количество процессоров.
- **42 сравнения:** граф `triadag10_0` (55 работ), 4, 8 и 16 процессоров, те же 7 эвристик и задержки 2 и 7.

Во всех экспериментах использовались `CR_bound = 0.4` и `random = 1234`. Для каждого сравнения обе программы получали одинаковые параметры и одну матрицу задержек.

**Итог: 350/350 PASS.** Расписания старой и новой программ совпали во всех проверенных комбинациях. Результаты сохранены в `results/heuristics_all.csv` и `results/heuristics_tri10.csv`.

## Эксперименты с разными значениями CR

Для автоматического запуска экспериментов используется `scripts/run_cr_experiments.py`.

Проверены следующие параметры:

- **Графы:** `triadag10_0` (10 слоёв, 55 работ), `triadag20_0` (20 слоёв, 210 работ), `triadag30_0` (30 слоёв, 465 работ)
- **Процессоры:** 4, 8, 16
- **CR_bound:** 0.2, 0.4, 0.6, 0.8
- **Задержки передачи:** 2 и 7
- **Эвристики:** `misf`, `eft`, `est`, `edfbase`, `edfb_misf`, `edffollow`, `edff_misf`
- **Random:** 1234
- **Критерий:** `CR`, при `CR2_bound = 0.0`

Всего проведено **504 сравнения**. Для каждой комбинации обе программы запускались с одинаковыми параметрами и матрицей задержек. Все 504 сравнения завершились успешно (`PASS`), расхождений между расписаниями не обнаружено.

Запуск полного набора экспериментов:

```bash
python3 scripts/run_cr_experiments.py
```

Результаты записываются в CSV после каждого эксперимента. При повторном запуске уже успешные проверки пропускаются. Для их повторного выполнения предусмотрен аргумент `--force`.

Итоговая таблица находится в `results/cr_experiments.csv`. Она содержит граф, число процессоров, CR, задержку, эвристику, random, статус и длительность расписания.

Для каждого эксперимента создаётся отдельная конфигурация. Исходные `config.toml` обеих программ не изменяются.

## Визуализация результатов экспериментов

Для построения сравнительных диаграмм используется `scripts/plot_cr_experiments.py`.

Данные берутся из `results/cr_experiments.csv`.

На диаграммах показано отношение длительности расписания каждой эвристики к длительности MISF при одинаковых параметрах:

`Cmax(heuristic) / Cmax(MISF)`

Значение 1 соответствует MISF, меньше 1 - результат лучше MISF, больше 1 - хуже.

Для каждой комбинации графа, числа процессоров и задержки строится отдельная диаграмма с четырьмя значениями CR (0.2, 0.4, 0.6, 0.8) и семью эвристиками.

Всего построено **18 диаграмм**.

Запуск генерации всех диаграмм:

```bash
python3 scripts/plot_cr_experiments.py
```

Результаты:
- `results/cr_charts/` - 18 отдельных PNG
- `results/cr_overview.png` - обзорный лист со всеми диаграммами
- `results/cr_charts.pdf` - PDF из 18 страниц, по одной диаграмме на каждой

Обзорный лист и PDF собраны из полученных отдельно PNG.
