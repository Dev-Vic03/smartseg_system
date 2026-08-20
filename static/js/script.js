function speakInsight(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Reset queue
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.lang = 'en-US';
        
        window.speechSynthesis.speak(utterance);
    } else {
        console.error("Speech Synthesis is not supported in this browser.");
    }
}