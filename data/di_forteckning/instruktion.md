# Avskrift av innehållsförteckningen i Diplomatarium Islandicum

Bilderna är sidor ur innehållsförteckningen ("Röð og efni bréfanna") i ett band av Diplomatarium Islandicum.
Varje post har brevets nummer, datering, en isländsk rubrik och sidan eller sidorna där brevet står.

Skriv av varje post som den står tryckt. Rätta inte och gissa inte. Om en siffra inte går att läsa, skriv `?`
på dess plats. En post som fortsätter från föregående sida tas med på den sida där numret står; en fortsättning
utan nummer överst på en sida hör till föregående post och skrivs inte som egen post.

För varje post, en rad JSON med fälten:
- `bild`: bildfilens namn
- `nr`: brevets nummer som det står (text, t.ex. "418" eller "41?")
- `datering`: dateringen som den står, t.ex. "1467, 13. Janúar" eller "[um 1330—40]"
- `rubrik`: rubriken, med avstavningar ihopsatta
- `sidor`: sidhänvisningen som den står, t.ex. "471—472" eller "15"

Skriv JSON Lines i bildernas och posternas ordning.
