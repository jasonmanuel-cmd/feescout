\# FeeScout API - Vercel Deployment



\## Quick Deploy (3 Commands)



```bash

npm i -g vercel

vercel login

vercel --prod

```



\## After Deployment



1\. Go to Vercel Dashboard: https://vercel.com/dashboard

2\. Click your "feescout" project

3\. Settings → Environment Variables

4\. Add:

&#x20;  - Name: `BLOCKCHAIR\_API\_KEY`

&#x20;  - Value: `G\_\_\_MTJ7PgczS9WHwUrUVqPVA4m4qqXf`

5\. Redeploy: `vercel --prod`



\## Test Your API



```

https://your-project.vercel.app/

https://your-project.vercel.app/api/gas-fees/cheapest

https://your-project.vercel.app/api/gas-fees/latest

```

