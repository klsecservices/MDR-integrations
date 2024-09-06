## Description

Интеграция TheHive и Kaspersky MDR реализуется с помощью Cortex: Responder.

## Administration

### Requirements

#### Software

TheHive 4.0 and above.

TheHive 3.x not tested

#### Packages

Python packages
```
requests
typing
time
yaml
json
cortexutils
```

#### TheHive configuration

CaseCustomField:

- Name: MDR Incident ID (or any other)
- Internal Reference: mdr-incident-id
- Description: MDR Incident ID
- Type: string

Для добавления поля необходимо перейти в Switch organisation (on the top tab) → admin → Admin (on the top tab) → Add custom field

### Installation

Скопировать папку с файлами в Cortex-Analyzers/responders/KasperskyMDR
Перезапустить службу cortex
Зайти в консоль Cortex, затем Organization → Responders → Type "MDR" → Enable → Edit
Заполнить поля для конфигурации. Если используется двухсторонняя интеграция, то достаточно указать лишь путь до файла config.yml из MDR Integration Utility.

## Integrations

### MDR_SendTaskLog

|   |   |
| - | - |
| **Name** | MDR_SendTaskLog |
| **Description** | Отправляет комментарий из задачи в инцидент MDR по incident_id, который берется из customField: mdr-incident-id. Responder для передачи комментария или вложения в KasperskyMDR. Чтобы им воспользоваться необходимо напротив комментария в задаче нажать Responders и выбрать MDR_SendTaskLog. При этом необходимо, чтобы CaseCustomField было заполнено информацией о incident_id в системе MDR. |
| **Object** | Case:CaseTaskLog |
| **Features** | DONE: Отправка текстовых комментариев<br> IN PROCESS: Отправка вложений<br> PROPOSED: Пометка комментария как успешно отправленного |

### MDR_CloseIncident

|   |   |
| - | - |
| **Name** | MDR_CloseIncident |
| **Description** | Закрывает инцидент в MDR |
| **Object** | Case |
| **Features** | IN PROCESS: Закрытие инцидента в MDR<br> IN PROCESS: Закрытие Case в TheHive<br> IN PROCESS: Возможность указать комментарии к закрытию |

### MDR_ApproveResponse

|   |   |
| - | - |
| **Name** | MDR_ApproveResponse |
| **Description** | В рамках созданной задачи по присланному Response от MDR Team отправляет подтверждение. |
| **Object** | Case:Task |
| **Features** | IN PROCESS: Отправка подтверждения для Response |

### MDR_CreateIncident

|   |   |
| - | - |
| **Name** | MDR_CreateIncident |
| **Description** | При создании Case есть возможность передать данные и создать соответствующий инцидент в MDR |
| **Object** | Case |
| **Features** | IN PROCESS: Создание инцидента в MDR<br> IN PROCESS: Связать инциденты через mdr-incident-id<br> IN PROCESS: Реализовать настройку, чтобы избежать дублирования инцидентов при синхронизации |

## Reference

**[TheHive API	TheHive4py Documentation](thehive-project.github.io)**


