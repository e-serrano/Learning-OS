import { useTranslation } from '../i18n/LanguageContext'
import './MasteryBar.css'

interface MasteryBarProps {
  /** 0..1, matching `GoalProgress.mastery` (docs/API_SPEC.md #10). */
  mastery: number
}

export function MasteryBar({ mastery }: MasteryBarProps) {
  const { t } = useTranslation()
  return (
    <div className="mastery-bar-row">
      <div className="mastery-bar">
        <div className="mastery-bar-fill" style={{ width: `${mastery * 100}%` }} />
      </div>
      <span>
        {Math.round(mastery * 100)}% {t('masteryBar.mastery')}
      </span>
    </div>
  )
}
