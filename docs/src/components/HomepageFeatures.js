import React from 'react';
import clsx from 'clsx';
import { Link } from 'react-router-dom';
import styles from './HomepageFeatures.module.css';

const FeatureList = [
  {
    title: 'Product workflow',
    docLink: '/docs/enterprise-insight-agent',
    description: (
      <>
        Follow research planning, evidence review, citation grounding, and inspectable report records in one workflow.
      </>
    ),
  },
  {
    title: 'Architecture and implementation',
    docLink: '/docs/enterprise-insight-agent#architecture-and-implementation',
    description: (
      <>
        See the core evidence records, claim checks, enterprise workflow, local API, and persistence modules.
      </>
    ),
  },
  {
    title: 'Evaluation and limitations',
    docLink: '/docs/enterprise-insight-agent#tests-and-evaluation',
    description: (
      <>
        Review the measured holdout outcome, frozen evaluation scope, and known gaps before relying on reports.
      </>
    ),
  },
];

function Feature({title, description, docLink}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <Link to={docLink}>
            <h3>{title}</h3>
        </Link>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container" style={{marginTop: 30}}>
        <div className="row" style={{justifyContent: 'center'}}>
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
