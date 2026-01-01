import { useState } from "react"
import App from "./App.jsx"
import LandingPage from "./LandingPage.jsx"

function Root() {
  const [started, setStarted] = useState(false)

  return started ? (
    <App />
  ) : (
    <LandingPage onStart={() => setStarted(true)} />
  )
}

export default Root
