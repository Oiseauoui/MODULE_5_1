> JS main.js > ...
Console.log('Hello wo rid!1) ft
const ws = new WebSocket('wsj://localhost:8080')
formChat.addEventListener(1 submit1, (e) => { e.preventDefault() ws.send textField.value textField.value = null
})
ws.onopen = (e) => {
console.log('Hello WebSocket!') }
ws.onmessage = (e) => {
console.log(e.data) text = e.data
const elMsg = document.createElement('div') elMsg.textcontent = text subscribe.appendchild(elMsg)
I