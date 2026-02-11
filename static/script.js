let recognition;

function startListening() {
    document.getElementById("recordingOverlay").style.display = "flex";

    if (!('webkitSpeechRecognition' in window)) {
        alert("Speech recognition not supported. Use Chrome.");
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.start();

    recognition.onresult = function(event) {
        let transcript = "";

        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }

        transcript = transcript.toLowerCase();
        document.getElementById("voiceText").innerText = "You said: " + transcript;

        autoFillForm(transcript);
    };

    recognition.onerror = function(event) {
        console.log("Speech error:", event.error);
    };
}


function stopListening() {
    document.getElementById("recordingOverlay").style.display = "none";

    if (recognition) {
        recognition.stop();
    }
}


function clearVoice() {
    document.getElementById("voiceText").innerText = "";

    // Reset dropdowns
    document.getElementById("gender").selectedIndex = 0;
    document.getElementById("occasion").selectedIndex = 0;
    document.getElementById("mood").selectedIndex = 0;
    document.getElementById("weather").selectedIndex = 0;
    document.getElementById("budget").selectedIndex = 0;
}


function autoFillForm(text) {

    if (text.includes("male") || text.includes("man")) {
        document.getElementById("gender").value = "Male";
    }

    if (text.includes("female") || text.includes("woman")) {
        document.getElementById("gender").value = "Female";
    }

    if (text.includes("wedding")) {
        document.getElementById("occasion").value = "Wedding";
    }

    if (text.includes("party")) {
        document.getElementById("occasion").value = "Party";
    }

    if (text.includes("office")) {
        document.getElementById("occasion").value = "Office";
    }

    if (text.includes("casual")) {
        document.getElementById("occasion").value = "Casual";
    }

    if (text.includes("elegant")) {
        document.getElementById("mood").value = "Elegant";
    }

    if (text.includes("bold")) {
        document.getElementById("mood").value = "Bold";
    }

    if (text.includes("minimal")) {
        document.getElementById("mood").value = "Minimal";
    }

    if (text.includes("trendy")) {
        document.getElementById("mood").value = "Trendy";
    }

    if (text.includes("low")) {
        document.getElementById("budget").value = "Low";
    }

    if (text.includes("medium")) {
        document.getElementById("budget").value = "Medium";
    }

    if (text.includes("high")) {
        document.getElementById("budget").value = "High";
    }

    if (text.includes("hot")) {
        document.getElementById("weather").value = "Hot";
    }

    if (text.includes("cold")) {
        document.getElementById("weather").value = "Cold";
    }

    if (text.includes("rainy")) {
        document.getElementById("weather").value = "Rainy";
    }

    if (text.includes("humid")) {
        document.getElementById("weather").value = "Humid";
    }
}
