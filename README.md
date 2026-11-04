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
