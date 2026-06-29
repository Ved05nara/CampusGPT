import { useState } from "react";
import API from "./services/api";

function App() {
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [sources, setSources] = useState([]);

    const askQuestion = async () => {

        if (!question.trim()) return;
        try {

            const response = await API.post("/query", {
                question: question
            });

            setAnswer(response.data.answer);
            setSources(response.data.sources);

        } catch (error) {

            console.error(error);

            setAnswer("Error getting response.");
        }
    };

    return (
        <div style={{
            maxWidth: "900px",
            margin: "50px auto",
            fontFamily: "Arial"
        }}>

            <h1>AI Study Assistant</h1>

            <textarea
                rows="4"
                style={{
                    width: "100%",
                    padding: "10px"
                }}
                value={question}
                onChange={(e) =>
                    setQuestion(e.target.value)
                }
                placeholder="Ask anything about your uploaded notes..."
            />

            <button
                onClick={askQuestion}
                style={{
                    marginTop: "10px",
                    padding: "10px 20px"
                }}
            >
                Ask
            </button>

            <hr />

            <h2>Answer</h2>

            <p>{answer}</p>

            <h2>Sources</h2>

            <ul>
                {sources?.map((source, index) => (
                    <li key={index}>
                        {source}
                    </li>
                ))}
            </ul>

        </div>
    );
}

export default App;