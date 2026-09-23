export function AppFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-brand">
        <div className="footer-brand-lockup">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <p className="footer-brand-name">EventLens</p>
        </div>
        <p className="footer-description">Explainable Event Matching</p>
        <p className="footer-event">HackAlem AI {'\u2022'} 2026</p>
      </div>

      <section className="footer-team" aria-labelledby="footer-team-heading">
        <h2 className="footer-team-heading" id="footer-team-heading">{'\u041A\u043E\u043C\u0430\u043D\u0434\u0430'}</h2>
        <ul className="footer-team-list">
          <li>YESSENALIYEV ARYSTANALI</li>
          <li>Artem Khloptsev</li>
          <li>Damir Kusmagambetov</li>
        </ul>
      </section>
    </footer>
  )
}