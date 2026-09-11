(() => {
  "use strict";

  // ---------- DOM refs ----------
  const inputText = document.getElementById("inputText");
  const targetLang = document.getElementById("targetLang");
  const toneSelect = document.getElementById("tone");
  const detectedLang = document.getElementById("detectedLang");

  const resultTag = document.getElementById("resultTag");
  const emptyState = document.getElementById("emptyState");
  const resultBody = document.getElementById("resultBody");
  const resultOutput = document.getElementById("resultOutput");
  const resultFooter = document.getElementById("resultFooter");
  const resultStatus = document.getElementById("resultStatus");
  const copyResultBtn = document.getElementById("copyResult");
  const replaceResultBtn = document.getElementById("replaceResult");

  const errorsPanel = document.getElementById("errorsPanel");
  const errorsToggle = document.getElementById("errorsToggle");
  const errorsCount = document.getElementById("errorsCount");
  const errorsList = document.getElementById("errorsList");

  const recordBtn = document.getElementById("recordBtn");
  const imageInput = document.getElementById("imageInput");

  const correctBtn = document.getElementById("correctBtn");
  const translateBtn = document.getElementById("translateBtn");
  const rephraseBtn = document.getElementById("rephraseBtn");

  let lastResultText = "";

  // État de la correction interactive en cours (permet de recalculer
  // le résultat quand l'utilisateur change une suggestion).
  let correctionState = null; // { baseText, choices: [{start,length,original,suggestions,selectedIndex}] }

  // ---------- helpers: unified result pane ----------
  function setResultTag(label, ready, isAi) {
    resultTag.textContent = label;
    resultTag.classList.toggle("is-ready", !!ready);
    resultTag.classList.toggle("is-ai", !!isAi);
  }

  function showResult(text, statusText) {
    lastResultText = text || "";
    emptyState.hidden = true;
    resultBody.hidden = false;
    resultOutput.textContent = text || "(Résultat vide)";
    resultFooter.hidden = false;
    resultStatus.textContent = statusText || "";
  }

  function showEmptyMessage(message) {
    emptyState.hidden = false;
    emptyState.querySelector("p").textContent = message;
    resultBody.hidden = true;
    resultFooter.hidden = true;
    errorsPanel.hidden = true;
    correctionState = null;
  }

  // Message honnête selon ce qui s'est réellement passé côté serveur :
  // on ne dit "corrigé" que si LanguageTool a réellement répondu.
  // La correction est TOUJOURS appliquée automatiquement (meilleure
  // suggestion) -- le panneau ci-dessous ne sert qu'à ajuster un choix
  // précis si l'utilisateur n'est pas d'accord, ce n'est jamais obligatoire.
  function describeCorrectionStatus(data) {
    if (!data.languagetool_available) {
      return "LanguageTool est injoignable : le texte n'a pas été vérifié (vérifiez que le serveur LanguageTool est lancé).";
    }
    if (!data.errors || data.errors.length === 0) {
      return "Vérifié avec LanguageTool : aucune erreur détectée.";
    }
    return "Corrigé automatiquement avec LanguageTool. Pas convaincu par une correction ? Ajustez-la ci-dessous.";
  }

  // Applique, sur baseText, la suggestion actuellement sélectionnée pour
  // chaque erreur (ou rien si l'utilisateur a choisi "garder l'original").
  // On applique du dernier au premier pour ne pas décaler les positions.
  function recomputeCorrectedText() {
    if (!correctionState) return "";

    const { baseText, choices } = correctionState;
    let result = baseText;

    const sorted = [...choices].sort((a, b) => b.start - a.start);
    for (const choice of sorted) {
      if (choice.selectedIndex === -1) continue; // "garder l'original"
      const replacement = choice.suggestions[choice.selectedIndex];
      if (replacement === undefined) continue;
      result = result.slice(0, choice.start) + replacement + result.slice(choice.start + choice.length);
    }

    return result;
  }

  function refreshCorrectionResult(statusText) {
    const text = recomputeCorrectedText();
    showResult(text, statusText);
  }

  function renderErrors(baseText, errors) {
    if (!errors || errors.length === 0) {
      errorsPanel.hidden = true;
      errorsList.innerHTML = "";
      correctionState = null;
      return;
    }

    correctionState = {
      baseText,
      choices: errors.map((err) => ({
        start: err.start,
        length: err.length,
        original: err.original,
        suggestions: err.suggestions || [],
        message: err.message,
        // par défaut, on propose la 1ère suggestion (mais rien n'est
        // appliqué tant que l'utilisateur ne confirme pas son choix)
        selectedIndex: err.suggestions && err.suggestions.length > 0 ? 0 : -1,
      })),
    };

    errorsPanel.hidden = false;
    errorsCount.textContent =
      errors.length === 1 ? "1 correction détectée" : `${errors.length} corrections détectées`;

    errorsList.innerHTML = "";

    correctionState.choices.forEach((choice, index) => {
      const li = document.createElement("li");

      const diff = document.createElement("div");
      diff.className = "error-diff";

      const original = document.createElement("span");
      original.className = "error-original";
      original.textContent = choice.original || "";
      diff.appendChild(original);

      if (choice.suggestions.length > 0) {
        const arrow = document.createElement("span");
        arrow.className = "error-arrow";
        arrow.textContent = "→";
        diff.appendChild(arrow);

        const select = document.createElement("select");
        select.className = "select error-select";
        select.setAttribute("aria-label", `Correction pour "${choice.original}"`);

        const keepOption = document.createElement("option");
        keepOption.value = "-1";
        keepOption.textContent = `Garder « ${choice.original} »`;
        select.appendChild(keepOption);

        choice.suggestions.forEach((s, sIndex) => {
          const opt = document.createElement("option");
          opt.value = String(sIndex);
          opt.textContent = s;
          select.appendChild(opt);
        });

        select.value = String(choice.selectedIndex);

        select.addEventListener("change", () => {
          correctionState.choices[index].selectedIndex = parseInt(select.value, 10);
          refreshCorrectionResult("Correction ajustée manuellement.");
        });

        diff.appendChild(select);
      }

      li.appendChild(diff);

      if (choice.message) {
        const msg = document.createElement("div");
        msg.className = "error-message";
        msg.textContent = choice.message;
        li.appendChild(msg);
      }

      // Bouton "Pourquoi ?" -- explication IA à la demande (jamais
      // appelée automatiquement, pour ne pas multiplier les requêtes).
      const explainBtn = document.createElement("button");
      explainBtn.type = "button";
      explainBtn.className = "error-explain-btn";
      explainBtn.textContent = "Pourquoi ?";
      explainBtn.addEventListener("click", () => {
        const chosenSuggestion =
          choice.selectedIndex >= 0 ? choice.suggestions[choice.selectedIndex] : choice.original;

        explainBtn.textContent = "Chargement…";
        explainBtn.disabled = true;

        fetch("/api/ai/explain", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            original: choice.original,
            suggestion: chosenSuggestion,
            sentence: correctionState.baseText,
          }),
        })
          .then((r) => r.json())
          .then((data) => {
            explainBtn.remove();
            const box = document.createElement("div");
            box.className = "error-ai-explanation";

            if (!data.ai_available) {
              box.innerHTML = '<span class="ai-label">IA</span>Indisponible : aucune clé DeepSeek configurée (voir .env).';
            } else if (!data.explanation) {
              box.innerHTML = '<span class="ai-label">IA</span>Explication indisponible pour le moment.';
            } else {
              box.innerHTML = '<span class="ai-label">Explication IA</span>' + data.explanation;
            }
            li.appendChild(box);
          })
          .catch(() => {
            explainBtn.textContent = "Erreur, réessayer ?";
            explainBtn.disabled = false;
          });
      });
      li.appendChild(explainBtn);

      errorsList.appendChild(li);
    });

    // reset collapsed state
    errorsToggle.setAttribute("aria-expanded", "false");
    errorsList.hidden = true;
  }

  errorsToggle.addEventListener("click", () => {
    const expanded = errorsToggle.getAttribute("aria-expanded") === "true";
    errorsToggle.setAttribute("aria-expanded", String(!expanded));
    errorsList.hidden = expanded;
  });

  const copyResultLabel = document.getElementById("copyResultLabel");

  copyResultBtn.addEventListener("click", () => {
    if (!lastResultText) return;
    navigator.clipboard.writeText(lastResultText).then(() => {
      const original = copyResultLabel.textContent;
      copyResultLabel.textContent = "Copié !";
      copyResultBtn.disabled = true;
      setTimeout(() => {
        copyResultLabel.textContent = original;
        copyResultBtn.disabled = false;
      }, 1600);
    });
  });

  replaceResultBtn.addEventListener("click", () => {
    if (lastResultText) inputText.value = lastResultText;
  });

  // ---------- Détection de langue (badge) ----------
  let detectTimer = null;
  let lastDetectedLang = "auto"; // langue détectée du texte d'entrée, réutilisée pour piloter le pivot vers le français avant Traduire/Reformuler

  function updateDetectedLangBadge() {
    const text = inputText.value.trim();
    if (!text) {
      detectedLang.hidden = true;
      lastDetectedLang = "auto";
      return;
    }

    fetch("/detect-language", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then((r) => r.json())
      .then((data) => {
        lastDetectedLang = data.language || "auto";
        if (!data.language_label) {
          detectedLang.hidden = true;
          return;
        }
        detectedLang.hidden = false;
        detectedLang.textContent = `${data.language_label} · confiance ${data.confidence.toLowerCase()}`;
        detectedLang.classList.toggle("is-darija", data.language === "darija");
        detectedLang.classList.toggle("is-amazigh", data.language === "amazigh");
      })
      .catch(() => {
        detectedLang.hidden = true;
      });
  }

  inputText.addEventListener("input", () => {
    clearTimeout(detectTimer);
    detectTimer = setTimeout(updateDetectedLangBadge, 500);
  });

  // ---------- Mode de traitement : automatique (IA si disponible, sinon règles) ----------
  // Plus de choix manuel : chaque endpoint /api/ai/* essaie l'IA en premier
  // et retombe silencieusement sur le pipeline par règles en cas d'échec
  // (clé absente, quota dépassé, erreur réseau...).

  // ---------- 1) CORRECTION (automatique : IA si dispo, sinon interactive par règles) ----------
  correctBtn.addEventListener("click", () => {
    const text = inputText.value.trim();
    setResultTag("Correction");
    errorsPanel.hidden = true;

    if (!text) {
      showEmptyMessage("Écrivez un texte avant de corriger.");
      return;
    }

    showEmptyMessage("Correction en cours…");
    correctionState = null;

    fetch("/api/ai/correct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.used_ai) {
          // L'IA a répondu : on affiche directement le résultat, sans
          // panneau de sélection par erreur (la réécriture est globale).
          showResult(data.corrected_text, "Corrigé par IA (Groq), avec compréhension du contexte.");
          setResultTag("Correction IA", true, true);
          return;
        }

        // IA indisponible (clé absente, quota, réseau...) : repli
        // transparent sur le pipeline par règles, avec le panneau
        // interactif habituel (sélection par erreur).
        fetch("/correct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        })
          .then((r) => r.json())
          .then((ruleData) => {
            renderErrors(ruleData.base_text, ruleData.errors);
            if (correctionState) {
              refreshCorrectionResult(describeCorrectionStatus(ruleData));
            } else {
              showResult(ruleData.base_text, describeCorrectionStatus(ruleData));
            }
            setResultTag("Correction", true);
          });
      })
      .catch(() => {
        showEmptyMessage("Erreur serveur. Vérifiez que Flask est lancé.");
      });
  });

  // Pivot FR "au mieux" pour Traduire/Reformuler.
  // - Texte déjà en français (ou détection incertaine) : IA "corrige en
  //   gardant la langue" en premier (comprend le sens, corrige mieux les
  //   fautes de frappe ambiguës comme "VUX" -> "veux"), pipeline par
  //   règles en repli.
  // - Texte détecté en Darija/Amazigh : on veut une VRAIE traduction
  //   vers le français, pas juste une correction dans la langue
  //   d'origine (/api/ai/correct préserve volontairement la langue,
  //   donc on ne l'utilise pas ici) -- on passe directement par le
  //   pivot dédié (IA si dispo, dictionnaire en repli), via /correct
  //   avec la langue détectée explicite.
  function fetchBestEffortFrench(text) {
    if (lastDetectedLang === "darija" || lastDetectedLang === "amazigh") {
      return fetch("/correct", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source_lang: lastDetectedLang }),
      })
        .then((r) => r.json())
        .then((data) => data.base_text || text);
    }

    return fetch("/api/ai/correct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then((r) => r.json())
      .then((aiData) => {
        if (aiData.used_ai && aiData.corrected_text) {
          return aiData.corrected_text;
        }

        return fetch("/correct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        })
          .then((r) => r.json())
          .then((data) => {
            let result = data.base_text || text;
            const sorted = [...(data.errors || [])].sort((a, b) => b.start - a.start);
            for (const err of sorted) {
              if (!err.suggestions || err.suggestions.length === 0) continue;
              result = result.slice(0, err.start) + err.suggestions[0] + result.slice(err.start + err.length);
            }
            return result;
          });
      });
  }

  // ---------- 2) TRADUCTION ----------
  translateBtn.addEventListener("click", () => {
    const text = inputText.value.trim();
    setResultTag("Traduction");
    errorsPanel.hidden = true;

    if (!text) {
      showEmptyMessage("Écrivez un texte avant de traduire.");
      return;
    }

    showEmptyMessage("Traduction en cours…");

    fetchBestEffortFrench(text)
      .then((corrected) =>
        fetch("/translate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: corrected,
            target_lang: targetLang.value,
            // fetchBestEffortFrench a déjà ramené le texte vers le
            // français (quelle que soit sa langue/écriture d'origine) --
            // /translate part donc toujours d'une base "fr" ici.
            source_lang: "fr",
          }),
        })
      )
      .then((r) => r.json())
      .then((data) => {
        const via = data.used_ai ? "IA" : "dictionnaire/service externe";
        showResult(data.translated_text, `Traduit vers ${targetLang.options[targetLang.selectedIndex].text} (${via}).`);
        setResultTag("Traduction", true, data.used_ai);
      })
      .catch(() => {
        showEmptyMessage("Erreur serveur pendant la traduction.");
      });
  });

  // ---------- 3) REFORMULATION (automatique : IA si dispo, sinon règles) ----------
  rephraseBtn.addEventListener("click", () => {
    const text = inputText.value.trim();
    setResultTag("Reformulation");
    errorsPanel.hidden = true;

    if (!text) {
      showEmptyMessage("Écrivez un texte avant de reformuler.");
      return;
    }

    showEmptyMessage("Reformulation en cours…");

    fetchBestEffortFrench(text)
      .then((corrected) => {
        return fetch("/api/ai/rewrite", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: corrected, tone: toneSelect.value }),
        })
          .then((r) => r.json())
          .then((data) => {
            const toneLabel = toneSelect.options[toneSelect.selectedIndex].text;
            if (data.used_ai) {
              showResult(data.rewritten_text, `Reformulé par IA (Groq) · ton : ${toneLabel}.`);
            } else {
              showResult(data.rewritten_text, `Reformulé par règles · ton : ${toneLabel}.`);
            }
            setResultTag(data.used_ai ? "Reformulation IA" : "Reformulation", true, data.used_ai);
          });
      })
      .catch(() => {
        showEmptyMessage("Erreur serveur pendant la reformulation.");
      });
  });

  // ---------- 4) OCR ----------
  imageInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("image", file);

    fetch("/ocr", {
      method: "POST",
      body: formData,
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.text !== undefined) {
          inputText.value = data.text;
          updateDetectedLangBadge();
        } else {
          alert(data.error || "Erreur pendant l'OCR.");
        }
      })
      .catch(() => alert("Erreur serveur pendant l'OCR."))
      .finally(() => {
        imageInput.value = "";
      });
  });

  // ---------- 5) Audio (Web Speech API, si disponible) ----------
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "fr-FR";
    recognition.interimResults = false;

    recognition.onstart = () => {
      recordBtn.classList.add("recording");
      recordBtn.querySelector(".tool-chip-icon").nextSibling.textContent = " Écoute en cours…";
    };
    recognition.onend = () => {
      recordBtn.classList.remove("recording");
      recordBtn.querySelector(".tool-chip-icon").nextSibling.textContent = " Enregistrer l'audio";
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      inputText.value = transcript;
      updateDetectedLangBadge();
    };
    recognition.onerror = (event) => {
      alert("Erreur de reconnaissance vocale : " + event.error);
    };

    recordBtn.addEventListener("click", () => {
      recognition.start();
    });
  } else {
    recordBtn.addEventListener("click", () => {
      alert("La reconnaissance vocale n'est pas supportée par ce navigateur.");
    });
  }

  // ---------- Reprise depuis la page d'accueil ----------
  // Si l'utilisateur a tapé du texte et choisi une action rapide sur
  // l'accueil, on le retrouve ici (sessionStorage) et on déclenche
  // automatiquement l'action correspondante.
  (() => {
    const pendingText = sessionStorage.getItem("linguora_pending_text");
    const pendingAction = sessionStorage.getItem("linguora_pending_action");
    sessionStorage.removeItem("linguora_pending_text");
    sessionStorage.removeItem("linguora_pending_action");

    if (pendingText) {
      inputText.value = pendingText;
      updateDetectedLangBadge();
    }

    switch (pendingAction) {
      case "correct":
        if (pendingText) correctBtn.click();
        break;
      case "translate":
        if (pendingText) translateBtn.click();
        break;
      case "rephrase":
        if (pendingText) rephraseBtn.click();
        break;
      case "ocr":
        imageInput.click();
        break;
      case "voice":
        recordBtn.click();
        break;
    }
  })();
})();
