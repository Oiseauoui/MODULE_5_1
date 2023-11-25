console.log('Hello world!');

const ws = new WebSocket('ws://localhost:8082');
const formChat = document.getElementById('formChat');
const textField = document.getElementById('textField');
const subscribe = document.getElementById('subscribe');
const numDaysField = document.getElementById('numDays');
const currenciesField = document.getElementById('currencies');

ws.onopen = (event) => {
    console.log('Hello WebSocket!');
    // Set default values or prompt the user for input here
    // const numDays = 3;
    // const currencies = ['EUR', 'USD'];
    // ws.send(`exchange ${numDays} ${currencies.join(' ')}`);

};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

formChat.addEventListener('submit', (event) => {
    event.preventDefault();
    ws.send(textField.value);
    textField.value = '';
});

ws.onmessage = (event) => {
    console.log(event.data);
    const text = event.data;

    const elMsg = document.createElement('div');
    elMsg.textContent = text;
    subscribe.appendChild(elMsg);
};
// function sendExchangeCommand() {
//   const numDays = numDaysField.value;
//   const currencies = currenciesField.value;
//   const command = `exchange ${numDays} ${currencies}`;
//   ws.send(command);
// }
