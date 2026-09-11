// Fonctions partagées entre la page d'accueil et l'espace de travail :
// upload OCR et reconnaissance vocale. Centralisées ici pour ne pas
// dupliquer la logique (voir static/js/app.js pour l'espace de travail).
window.LinguoraCapture = (function () {
  "use strict";

  function runOcrUpload(file, { onStart, onSuccess, onError } = {}) {
    if (!file) return;
    if (onStart) onStart();

    const formData = new FormData();
    formData.append("image", file);

    fetch("/ocr", { method: "POST", body: formData })
      .then((r) => r.json())
      .then((data) => {
        if (data.text !== undefined) {
          if (onSuccess) onSuccess(data.text);
        } else if (onError) {
          onError(data.error || "Erreur pendant l'OCR.");
        }
      })
      .catch(() => {
        if (onError) onError("Erreur serveur pendant l'OCR.");
      });
  }

  function isSpeechSupported() {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  function runSpeechRecognition({ onStart, onResult, onEnd, onError } = {}) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (onError) onError("La reconnaissance vocale n'est pas supportée par ce navigateur.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "fr-FR";
    recognition.interimResults = false;

    recognition.onstart = () => {
      if (onStart) onStart();
    };
    recognition.onend = () => {
      if (onEnd) onEnd();
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (onResult) onResult(transcript);
    };
    recognition.onerror = (event) => {
      if (onError) onError(event.error);
    };

    recognition.start();
  }

  return { runOcrUpload, runSpeechRecognition, isSpeechSupported };
})();
