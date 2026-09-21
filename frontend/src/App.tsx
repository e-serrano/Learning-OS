import { useCallback, useState } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { OnboardingWizard } from './onboarding/OnboardingWizard'
import { AppRoutes } from './shell/routes'

function App() {
  const [onboarded, setOnboarded] = useState(false)
  const handleFinished = useCallback(() => setOnboarded(true), [])

  if (!onboarded) {
    return <OnboardingWizard onFinished={handleFinished} />
  }

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App
