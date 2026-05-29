# Smoke mapper v3 sobre triangulación 2026-04-18

**Fecha ejecución:** 2026-05-09  
**Mapper version:** v3.0.0  
**Input:** 60 comments triangulados (Claude+Gemini+Gemma)

## Resumen ejecutivo

- **Comments procesados:** 60
- **Mapeos válidos (sin fallback):** 60 / 60 (100%)
- **Fallbacks:** 0 (0.0%)
- **Tono 3/3 acuerdo modelos:** 44/60 (73%)
- **Target 3/3 acuerdo modelos:** 38/60 (63%)

## Distribución tono

**Runner Gemma (input):**

- `elogio`: 24
- `critica`: 15
- `ataque`: 8
- `personal`: 4
- `informativo`: 4
- `pregunta`: 3
- `autopromocion`: 2

**Mapper v2 (output):**

- `celebratorio`: 26
- `critico`: 15
- `ataque`: 8
- `informativo`: 7
- `personal`: 4

## Distribución target

**Runner Gemma (input):**

- `dirigente_post`: 41
- `gobierno`: 10
- `institucion`: 4
- `oposicion`: 3
- `ciudadania`: 2

**Mapper v2 (output):**

- `dirigente`: 39
- `gobierno`: 10
- `tema_especifico`: 4
- `oposicion`: 3
- `ciudadania`: 2
- `autopromocion`: 2

## Flags activados (G1-G5)

- `pregunta_default`: 3
- `from_runner_autopromocion`: 2

## Stats mapper

```
  total: 60
  fallbacks: 0
  fallback_rate: 0.0
  autopromo_runtime: 0
  pregunta_to_critico: 0
  pregunta_to_informativo: 3
  emoji_breve: 0
```

## Sample 15 rows

| id | tono_runner→tono_v2 | target_runner→target_v2 | 3/3 | flags |
|---|---|---|---|---|
| IG_3642138545329726026_17861718855410453 | elogio→**celebratorio** | dirigente_post→**dirigente** | ✓ |  |
| IG_3735502669264799350_18045325463381143 | personal→**personal** | dirigente_post→**dirigente** | · |  |
| IG_3803860272113545357_17976357209809424 | elogio→**celebratorio** | dirigente_post→**dirigente** | · |  |
| IG_3828405263968328250_18056458157398724 | pregunta→**informativo** | dirigente_post→**dirigente** | ✓ | pregunta_default |
| IG_3841492975864320148_17950533843086325 | elogio→**celebratorio** | dirigente_post→**dirigente** | ✓ |  |
| IG_3852632659449958414_18183987799371610 | elogio→**celebratorio** | dirigente_post→**dirigente** | ✓ |  |
| IG_3859474251099511440_17864677434657041 | critica→**critico** | dirigente_post→**dirigente** | · |  |
| IG_3859474251099511440_17885517891466451 | critica→**critico** | dirigente_post→**dirigente** | ✓ |  |
| IG_3859474251099511440_17986748999974992 | informativo→**informativo** | gobierno→**gobierno** | · |  |
| IG_3863926554967780493_18322032121266928 | personal→**personal** | dirigente_post→**dirigente** | ✓ |  |
| IG_3866786064979863718_17866479906609089 | critica→**critico** | gobierno→**gobierno** | ✓ |  |
| IG_3866786064979863718_18098100671286102 | elogio→**celebratorio** | dirigente_post→**dirigente** | ✓ |  |
| IG_3866786064979863718_18106237537878841 | critica→**critico** | gobierno→**gobierno** | ✓ |  |
| IG_3869699613314075094_18113102713702495 | critica→**critico** | dirigente_post→**dirigente** | ✓ |  |
| IG_3869730475807385651_17995161773761144 | elogio→**celebratorio** | dirigente_post→**dirigente** | ✓ |  |
