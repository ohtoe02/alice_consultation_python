# Навык Алисы для консультации по курсам и записи на них

### Локальное тестирование
Чтоб локально запустить сервис, нужно:
1. Зарегистрироваться на [ngrok](https://ngrok.com/) и [скачать программу](https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip)
2. Распаковать программу и запустить
3. В открывшейся консоли прописать `ngrok authtoken ваш_токен`, сам токен доступен после регистрации [здесь](https://dashboard.ngrok.com/get-started/your-authtoken)
4. После прописать `ngrok http 3001`, если вы поменяли порт в main.py, то замените 3001 на тот, который вы установили
5. Скопировать подчеркнутую строку <img src="https://user-images.githubusercontent.com/68995714/161825601-465bd266-1f27-4e81-a1c8-d33175a6a956.png">
6. Вставить скопированную строку на этом [сайте](https://station.aimylogic.com/) и добавить к ней то, что написано в переменной WEBHOOK_URL_PATH в main.py <img src="(https://user-images.githubusercontent.com/68995714/161827107-bf239e7e-4431-4a92-bdc8-01bf58f70f28.png)
">
