# 민속 레트로 화면의 포함 글꼴

이 폴더의 WOFF2 글꼴은 아래 Google Fonts 저장소의 TTF에서 형식을 변환한 파일입니다. 글리프는 삭제하지 않았으며, 변환본의 기본 글꼴 이름을 `YutBrush`, `YutHand`로 변경했습니다. 화면에 쓸 때는 `font_bundle.py`가 파일을 직접 포함하므로 외부 글꼴 서버에 연결하지 않습니다.

| 포함 파일 | 원본 글꼴 | 사용 위치 | 동봉 라이선스 |
|---|---|---|---|
| `YutBrush-Regular.woff2` | Nanum Brush Script / 나눔 손글씨 붓 | 현수막·큰 제목 | `nanumbrushscript-OFL.txt` |
| `YutHand-Regular.woff2` | Yeon Sung / 연성 | 팀 이름·결과·보조 제목 | `yeonsung-OFL.txt` |

두 글꼴과 변환본은 **SIL Open Font License 1.1**에 따라 포함했습니다. 원본의 저작권·라이선스 메타데이터를 유지했으며, 전체 라이선스를 같은 폴더에 동봉했습니다. 미리보기 HTML에 포함되는 글꼴 CSS에도 해당 라이선스가 들어 있습니다.

## 원본 출처

- [Google Fonts: Nanum Brush Script](https://github.com/google/fonts/tree/main/ofl/nanumbrushscript)
- [Google Fonts: Yeon Sung](https://github.com/google/fonts/tree/main/ofl/yeonsung)
- [Google Fonts 한국어 소개](https://googlefonts.github.io/korean/)

이 안내는 원저작자의 보증이나 후원을 뜻하지 않습니다. 변환본을 별도로 배포할 때에도 동봉한 라이선스를 함께 유지해 주세요.
