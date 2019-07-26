const Koa = require('koa'), Router = require('koa-router'), Logger = require('koa-logger'), Session = require('koa-session'), Send = require('koa-send'), redisStore = require('koa-redis')
const util = require('util'), child_process = require('child_process'), which = require('which'), path = require('path'), fs = require('fs')
const crypto = require('crypto')

const PYTHON = which.sync('python')
const execFile = util.promisify(child_process.execFile)
const readFile = util.promisify(fs.readFile)

const app = new Koa()
const router = new Router()

app.keys = [crypto.randomBytes(32).toString('hex')]
const CONFIG = {
	store: redisStore()
}
const TIMEOUT = 300;

router.get('/', async (ctx, next) => {
	await Send(ctx, 'templates/index.html')
})

router.get('/state', async (ctx, next) => {
	ctx.set('Content-Type', 'application/json')
	ctx.body = JSON.stringify(ctx.session)
})

router.get('/generate', async (ctx, next) => {
	const _path = (await execFile(PYTHON,
		[__dirname + '/mbagen.py'])).stdout.toString('utf-8').trim()

	console.info(_path)
	ctx.session.current = _path
	ctx.session.current_date = new Date().getTime()
	ctx.session.save()

	ctx.redirect('/current')
})

router.get('/current', async (ctx, next) => {
	const _path = ctx.session.current
	if(_path === null) {
		ctx.redirect('/')
	}
	else
		await Send(ctx, path.basename(_path), { root: path.dirname(_path) })
})

router.get('/solution', async (ctx, next) => {
	const { solution } = ctx.request.query;
	ctx.set('Content-Type', 'application/json')

	if (ctx.session.current === null) {
		ctx.body = '"click start first"'
		return
	}

	if (!(typeof solution == "string") || !/^(\d+,){7}\d+$/.exec(solution)) {
		ctx.body = '"solution= must be string with format /^(\\d+,){7}\\d+$/"'
		return
	}

	if (ctx.session.current_date < (new Date().getTime()) - 1000 * TIMEOUT) {
		ctx.body = '"too late!"'
		return
	}

	const target = ctx.session.current.replace('.zip', '') + '.solution'
	const valid = solution == (await readFile(target)).toString('utf-8')

	fs.unlinkSync(target)
	fs.unlinkSync(ctx.session.current)

	if (valid) {
		ctx.session.level++;
		ctx.session.current = ctx.session.current_date = null
		if (ctx.session.level > 8) {
			ctx.session.flag = (await readFile('/flag')).toString('utf-8')
		}
		ctx.redirect('/')
	} else {
		ctx.body = 'nope!'
		ctx.session = null
	}
})

const init_session = async (ctx, next) => {
	const date = new Date().getTime()
	if (!ctx.session.init)
		ctx.session = null

	if(ctx.session && ctx.session.current_date && ctx.session.current_date < (date - 1000 * TIMEOUT)) {
		ctx.session = null
	}

	ctx.session = ctx.session || {
		init: true,
		current: null,
		current_date: null,
		server_date: null,
		level: 1,
		flag: null
	}

	ctx.session.server_date = date

	await next()
}

app
	.use(Session(CONFIG, app))
	.use(Logger())
	.use(init_session)
	.use(router.routes())
	.use(router.allowedMethods())

app.listen(80)
