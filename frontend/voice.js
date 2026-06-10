function speak(text, lang = "en-IN") {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();

  const msg = new SpeechSynthesisUtterance(text);
  msg.lang = lang;
  msg.rate = 0.95;
  window.speechSynthesis.speak(msg);
}
let voiceEnabled = false;

document.addEventListener("click", () => {
  voiceEnabled = true;
});

function speak(text, lang = "en-IN") {
  if (!voiceEnabled) return;

  window.speechSynthesis.cancel();
  const msg = new SpeechSynthesisUtterance(text);
  msg.lang = lang;
  window.speechSynthesis.speak(msg);
}