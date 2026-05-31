# Источники стандартов: ГОСТ Р 52872-2019 и WCAG

Где взять авторитетные тексты для `engine/catalog.data.ts` (реестр ГОСТ↔WCAG).
Найдено веб-поиском; ссылки проверены где возможно.

> **Ключевой факт для маппинга:** по официальной карточке Росстандарта ГОСТ Р
> 52872-2019 гармонизирован с **WCAG 2.1** (введён 01.04.2020, приказ Росстандарта
> № 589-ст от 29.08.2019). То есть пункты ГОСТ трассируются на критерии WCAG **2.1**,
> а не 2.2. WCAG 2.2 можно использовать в remediation, но базовая линия маппинга — 2.1.
> Это расходится с текущим `CLAUDE.md` (там 2.2) — решить при сборке каталога.

---

## ГОСТ Р 52872-2019

Полное название: «Интернет-ресурсы и другая информация, представленная в
электронно-цифровой форме. Приложения для стационарных и мобильных устройств,
иные пользовательские интерфейсы. Требования доступности для людей с
инвалидностью и других лиц с ограничениями жизнедеятельности».

> Примечание: в РФ официальная полная копия ГОСТ продаётся через Росстандарт.
> Бесплатные зеркала несут тот же текст, но не являются «официальной» копией.
> Для цитирования пунктов в инструменте текста с cntd.ru / Гарант достаточно;
> для юридической ссылки — protect.gost.ru.

**Авторитетный реестр (статус, реквизиты, официальная копия):**
- Росстандарт, карточка документа — [protect.gost.ru/document.aspx?control=7&id=233736](https://protect.gost.ru/document.aspx?control=7&id=233736)
  (US-only fetch отказал; открыть из РФ-сети)

**Бесплатный полный текст (зеркала):**
- Кодекс/Техэксперт — [docs.cntd.ru/document/1200167693](http://docs.cntd.ru/document/1200167693)
- Гарант — [base.garant.ru/73664694/](https://base.garant.ru/73664694/)
- Тифлоцентр, прямой PDF — [tiflocentre.ru/download/gost-r-52872-2019.pdf](https://tiflocentre.ru/download/gost-r-52872-2019.pdf)
  (и страница [tiflocentre.ru/documents/gost-r-52872-2019.php](https://tiflocentre.ru/documents/gost-r-52872-2019.php))
- Прямой PDF (зеркало cntd) — [anosov.ru/files/BPOO/52872_2019.pdf](https://www.anosov.ru/files/BPOO/52872_2019.pdf)
- standartgost — [standartgost.ru/g/ГОСТ_Р_52872-2019](https://standartgost.ru/g/%D0%93%D0%9E%D0%A1%D0%A2_%D0%A0_52872-2019)
- meganorm / stroyinf (скан) — [meganorm.ru/Index2/1/4293727/4293727086.htm](https://meganorm.ru/Index2/1/4293727/4293727086.htm)
- vsegost — [vsegost.com/Catalog/71/71634.shtml](https://vsegost.com/Catalog/71/71634.shtml)

---

## WCAG (официально, бесплатно, у W3C)

**Нормативные рекомендации:**
- WCAG 2.1 (база гармонизации ГОСТ) — [w3.org/TR/WCAG21/](https://www.w3.org/TR/WCAG21/)
- WCAG 2.2 (актуальная, для remediation) — [w3.org/TR/WCAG22/](https://www.w3.org/TR/WCAG22/)

**Пояснения и навигация:**
- Understanding WCAG 2.2 — [w3.org/WAI/WCAG22/Understanding/](https://www.w3.org/WAI/WCAG22/Understanding/)
- How to Meet (Quickref, фильтруемый) — [w3.org/WAI/WCAG22/quickref/](https://www.w3.org/WAI/WCAG22/quickref/)

**Машиночитаемый JSON — лучший seed для `catalog.data.ts`:**
- Официальный — [w3.org/WAI/WCAG22/wcag.json](https://www.w3.org/WAI/WCAG22/wcag.json)
  ✅ проверено: principles → guidelines → success criteria с полями
  `id`, `num` (напр. `1.1.1`), `level` (`A`/`AA`/`AAA`), `versions`
  (`["2.0","2.1","2.2"]`), techniques. Идеально для импорта SC уровня AA.
- Данные Quickref — [github.com/w3c/wai-wcag-quickref/blob/gh-pages/_data/wcag2.json](https://github.com/w3c/wai-wcag-quickref/blob/gh-pages/_data/wcag2.json)
- Сообщество (миррор) — [github.com/tenon-io/wcag-as-json](https://github.com/tenon-io/wcag-as-json)

---

## Как это ложится в pivot

1. `wcag.json` фильтруем по `level ∈ {A, AA}` → автоматический скелет WCAG-стороны
   каталога (без ручного переписывания критериев — то, что и просили).
2. ГОСТ-сторона (номера + названия пунктов) — из текста cntd.ru / Гарант, сверяется
   человеком; маппинг ГОСТ↔WCAG помечается `provisional` до экспертной валидации
   (открытый вопрос №1 в `docs/architecture-plan.md`).
3. `versions` в `wcag.json` позволяет в одном файле держать и 2.1-трассировку (ГОСТ),
   и 2.2-remediation.
