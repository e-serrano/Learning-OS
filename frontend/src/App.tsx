import { useCallback, useState } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { LanguageProvider } from './i18n/LanguageContext'
import { OnboardingWizard } from './onboarding/OnboardingWizard'
import { AppRoutes } from './shell/routes'

function App() {
  const [onboarded, setOnboarded] = useState(false)
  const handleFinished = useCallback(() => setOnboarded(true), [])

  return (
    <LanguageProvider>
      {onboarded ? (
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      ) : (
        <OnboardingWizard onFinished={handleFinished} />
      )}
    </LanguageProvider>
  )
}

export default App
