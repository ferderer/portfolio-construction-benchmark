# Warum regelbasierte Portfolio-Konstruktion die richtige Architektur-Entscheidung ist

*Ein empirischer Vergleich von drei Konstruktionsmethoden auf 20 Jahren Marktdaten – und was das für Multi-Tenant-Plattformen in der Vermögensverwaltung bedeutet.*

---

## Die Ausgangsfrage

Wer eine Plattform für digitale Vermögensverwaltung entwickelt, steht früh vor einer Architektur-Entscheidung: Wie konstruiert das System Kundenportfolios? Die Antwort hat Auswirkungen weit über die Quantitative-Finance-Abteilung hinaus – auf Infrastruktur, Betriebskosten, Auditierbarkeit und regulatorische Compliance.

Die drei gängigen Ansätze:

* **Markowitz Mean-Variance-Optimierung** — mathematisch optimal, in der Praxis instabil
* **Black-Litterman** – stabilere Variante mit quantifizierten Marktmeinungen
* **Regelbasiert** — feste Zielallokation mit schwellenwertbasiertem Rebalancing

Ich habe alle drei implementiert und auf 20 Jahren realer ETF-Daten (2004–2024) verglichen. Das Ergebnis ist eindeutig – und hat direkte Implikationen für die Systemarchitektur.

## Die Ergebnisse

Vier ETFs (SPY, EEM, AGG, VNQ), identische Constraints, kein Lookahead-Bias:

|                   | Regelbasiert |   Markowitz | Black-Litterman |
|-------------------|-------------:|------------:|----------------:|
| **CAGR**          |   **8,76 %** |      8,15 % |          7,12 % |
| Volatilität       |      15,89 % | **11,83 %** |         23,27 % |
| Sharpe Ratio      |        0,425 |   **0,520** |           0,220 |
| jährl. Turnover   |    **102 %** |       223 % |           236 % |
| Rebalancings      |      **211** |         677 |             501 |
| Tracking Error    |   **0,95 %** |      7,45 % |          8,70 % |

Der Markowitz-Optimierer liefert die beste risikoadjustierte Rendite (Sharpe 0,520). Aber er erreicht das durch Konzentration auf zwei von vier Assetklassen: 60 % S&P 500, 40 % US-Anleihen, 0 % Emerging Markets, 0 % Immobilien – über Jahre. Das ist kein Fehler im Algorithmus. Es ist ein *Mandats-Mismatch*: Ein „Balanced Growth“-Risikoprofil, das diversifizierte Exponierung verspricht, kann nicht 0 % in zwei Assetklassen liefern.

## Transaktionskosten verstärken den Effekt

| Strategie       | CAGR-Verlust bei 20 bps |
|-----------------|------------------------:|
| Regelbasiert    |           **−0,01 Pp.** |
| Markowitz       |               −0,23 Pp. |
| Black-Litterman |               −0,28 Pp. |

Markowitz verliert 23-mal mehr an Transaktionskosten als der regelbasierte Ansatz. Bei steuerpflichtigen Depots kommen realisierte Kapitalerträge als zusätzlicher Kostenfaktor hinzu.

## Architektur-Implikationen

Die Wahl des Portfolio-Konstruktionsmodells ist eine Architektur-Entscheidung. Drei Dimensionen sind entscheidend:

**Skalierbarkeit.** Regelbasiertes Rebalancing prüft pro Portfolio einen Schwellwert – eine Operation im Mikrosekundenbereich. Mean-Variance-Optimierung erfordert Kovarianzmatrix-Berechnung, numerische Optimierung und Constraint-Handling pro Portfolio. Bei einer Plattform mit 400 000 Portfolios über 875 White-Label-Mandanten bestimmt dieser Unterschied den Infrastrukturbedarf.

**Auditierbarkeit.** Die BaFin erwartet nachvollziehbare Anlageentscheidungen. Ein regelbasiertes System dokumentiert: „Allokation wich um 6,2 % vom Ziel ab → Rebalancing ausgelöst.“ Ein Optimierer dokumentiert: „Kovarianzmatrix aus rollendem 3-Jahres-Fenster ergab optimale Gewichte [0,60, 0,00, 0,40, 0,00].“ Der zweite Audit-Trail erklärt das *Was*, aber nicht das *Warum*.

**Betriebskomplexität.** Optimierungsbasierte Modelle erfordern zusätzliche Infrastruktur: Rolling-Window-Berechnung, Model-Monitoring, Drift-Detection für Eingabedaten. Regelbasierte Systeme sind konfigurationsgetrieben – Zielgewichte und Schwellwerte in einer Config-Datei, keine ML-Pipeline.

## MiFID II und die Geeignetheitsprüfung

Die europäische Finanzmarktrichtlinie MiFID II verlangt, dass jede Anlageempfehlung für den konkreten Kunden *geeignet* ist (Art. 25 Abs. 2). Die Geeignetheitsprüfung erfordert, dass die Anlagelogik transparent und nachvollziehbar ist.

Ein regelbasiertes System erfüllt diese Anforderung unmittelbar: Der Kunde wählt ein Risikoprofil, das Profil definiert eine Zielallokation, Abweichungen werden periodisch korrigiert. Jeder Schritt ist auditierbar.

Bei optimierungsbasierten Ansätzen wird die Geeignetheitsprüfung anspruchsvoller. Wenn der Optimierer entscheidet, dass das Portfolio eines konservativ eingestuften Kunden 0 % Anleihen halten sollte – weil die rollierende Kovarianzschätzung das nahelegt –, muss die Plattform erklären können, warum diese Entscheidung dem Kundenprofil entspricht.

## Robustheit

Das Ergebnis hängt nicht an einer spezifischen Zielallokation. Drei Varianten zwischen 50 % und 70 % Aktienquote bestätigen das Muster:

| Variante                  | CAGR       | Turnover  |
|---------------------------|-----------:|----------:|
| 70/10/15/5 (offensiv)     |     9,35 % |      81 % |
| **60/15/20/5 (Standard)** | **8,76 %** | **102 %** |
| 50/20/25/5 (moderat)      |     8,16 % |     119 % |

Alle drei Varianten übertreffen Black-Litterman. Die spezifischen Gewichte sind weniger entscheidend als der Ansatz.

Zusätzlich zeigt eine Sensitivitätsanalyse der Rebalancing-Frequenz: Halbjährliche Prüfungen mit ±10 % Schwellwert liefern 9,36 % CAGR – das beste Ergebnis aller getesteten Konfigurationen. Weniger prüfen, weniger handeln, bessere Ergebnisse.

## Fazit

In der digitalen Vermögensverwaltung für Retail-Kunden sind die Anforderungen — Regulatorik, Erklärbarkeit, Skalierbarkeit, Kosteneffizienz — keine Einschränkungen des Optimierungsproblems. **Sie definieren, was optimal bedeutet.**

Der vollständige Benchmark mit Open-Source-Implementierung und ausführlicher Methodik ist verfügbar unter: [GitHub-Link](https://github.com/ferderer/portfolio-construction-benchmark)

---

*Vadim Ferderer ist Senior Software Engineer bei der adesso SE BL Banking Line mit Schwerpunkt Performance-Optimierung und Architektur.*
