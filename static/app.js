function emit_download(url) {
	let aTag = document.createElement('a');
	aTag.download = '';
	aTag.href = url;
	aTag.click()
}

const opts = { dark: false };
Vue.use(Vuetify);

const Index = { template: '<div>test index</div>' }

Vue.component('log-file', {
	template: `
	<div>
		{{ filename }} <v-btn text icon small v-on:click="download_log()"><v-icon>mdi-download</v-icon></v-btn>
		<v-textarea :value="file_content" style="font-size:10px" rows="25" no-resize readonly></v-textarea>
	</div>
	`,
	props: ['filename'],
	data: function() {
		return {
			file_content: ''
		}
	},
	created: function() {
		console.log('ok');
		axios.get('/api/log/' + this.filename).then(response => {
			this.file_content = response.data.data;
		})
	},
	methods: {
		download_log: function() {
			axios.get('/api/log/' + this.filename + '/download').then(response => {
				emit_download(response.data.data);
			})
		}
	}
})

const Album = {
	template: `
	<div>
		<v-row>
			<v-col sm="4"><v-card outlined><v-img :key="cover_default" :src="cover_default"></v-img></v-card></v-col>
			<v-col sm="8">
				<v-card-title> {{ title }} </v-card-title>
				<v-card-text>
					Artist: {{ artist }} <br>
					Release date: {{ release_date || 'Unknown' }} <br>
					Format: {{ format + ', ' + quality + ' (' + quality_details + ')'}} <br>
					Source: {{ source && file_source ? source + ', ' + file_source : source || file_source || 'Unknown' }} <br>
					Trusted: {{ trusted ? 'yes' : 'no' }} <br>
					Comments: {{ comments }} <br>
					<v-btn text small @click="edit()">Edit</v-btn>
				</v-card-text>
			</v-col>
		</v-row>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left"></th>
					<th class="text-left"></th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="item in songs" :key="'song' + item.id">
					<td>{{ item.track }}</td>
					<td><v-btn text icon small><v-icon>mdi-play-circle</v-icon></v-btn></td>
					<td><v-btn text icon small v-on:click="download_song(item)"><v-icon>mdi-download</v-icon></v-btn></td>
					<td>{{ item.title }}</td>
					<td>{{ item.duration }}</td>
					<td>{{ item.artist }}</td>
				</tr>
			</tbody>
		</v-simple-table>
		<v-tabs vertical class="v-tab-no-upper-case">
			<v-tab> Scans </v-tab>
			<v-tab> Logs </v-tab>
			<v-tab> Other files </v-tab>
			<v-tab-item>todo</v-tab-item>
			<v-tab-item>
				<v-card-text v-if="log_files.length">
					<log-file v-for="item in log_files" :key="'log' + item" :filename="item"></log-file>
				</v-card-text>
				<v-card-text v-else>
					There's no log files for this album now.
				</v-card-text>
			</v-tab-item>
			<v-tab-item>todo3</v-tab-item>
		</v-tabs>
	</div>
	`,
	data: function() {
		return {
			id: -1,
			title: '',
			release_date: null,
			artist: '',
			format: '',
			quality: '',
			quality_details: '',
			source: '',
			file_source: '',
			trusted: '',
			log_files: [],
			cover_files: [],
			comments: '',
			songs: []
		}
	},
	computed: {
		cover_default: function() {
			return this.cover_files.length ? this.cover_files[0] : 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY/j//z8DAAj8Av6IXwbgAAAAAElFTkSuQmCC';
		}
	},
	watch: {
		id: function(new_id, old_id) {
			this.init()
		}
	},
	created: function() {
		this.id = this.$route.params.id;
		this.init();
	},
	methods: {
		init: function() {
			axios.get('/api/album/' + this.id + '/info').then(response => {
				for (key in response.data.data)
					this[key] = response.data.data[key];
			})
		},
		download_song: function(item) {
			axios.get('/api/song/' + item.id + '/link').then(response => {
				emit_download(response.data.data.file);
			})
		},
		edit: function() {
			console.log(this.$route.params.id);
			this.$router.push({ name: 'album_edit', params: { id: this.id } });
		}
	}
}

const AlbumEdit = {
	template: `
	<div>
		<v-row>
			<v-card-title> Edit: {{ title }} </v-card-title>
			<v-card-text>
				<v-text-field v-model="title" label="Title"></v-text-field>
				<v-text-field v-model="artist" label="Artist"></v-text-field>
				<v-text-field v-model="release_date" label="Release date"></v-text-field>
				<v-text-field v-model="source" label="Source"></v-text-field>
				<v-text-field v-model="file_source" label="File source"></v-text-field>
				<v-text-field v-model="comments" label="Comments"></v-text-field>
				<v-checkbox v-model="trusted" label="Trusted"></v-checkbox>
			</v-card-text>
		</v-row>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="item in songs" :key="'song' + item.id">
					<td><v-text-field v-model="item.track"></v-text-field></td>
					<td><v-text-field v-model="item.title"></v-text-field></td>
					<td>{{ item.duration }}</td>
					<td><v-text-field v-model="item.artist"></v-text-field></td>
				</tr>
			</tbody>
		</v-simple-table>
		<v-btn class="no-upper-case" outlined @click="submit">Confirm</v-btn>
	</div>
	`,
	data: function() {
		return {
			id: -1,
			title: '',
			release_date: null,
			artist: '',
			format: '',
			quality: '',
			quality_details: '',
			source: '',
			file_source: '',
			trusted: '',
			log_files: [],
			cover_files: [],
			comments: '',
			songs: []
		}
	},
	watch: {
		id: function(new_id, old_id) {
			this.init()
		}
	},
	created: function() {
		this.id = this.$route.params.id;
		this.init();
	},
	methods: {
		init: function() {
			axios.get('/api/album/' + this.id + '/info').then(response => {
				for (key in response.data.data)
					this[key] = response.data.data[key];
			})
		},
		submit: function() {
			console.log(this.trusted);
			var tmp = {
				title: this.title,
				release_date: this.release_date,
				artist: this.artist,
				source: this.source,
				file_source: this.file_source,
				comments: this.comments,
				trusted: this.trusted,
				songs: this.songs,
			};
			axios.post('/api/album/' + this.id + '/update', tmp).then(response => {
				this.$router.push({ name: 'album', params: { id: this.id } });
			})
		}
	}
}

const router = new VueRouter({
	routes: [
		{ path: '/', component: Index },
		{ path: '/album/:id', component: Album, name: 'album' },
		{ path: '/album/:id/edit', component: AlbumEdit, name: 'album_edit' }
	]
})

new Vue({
	router,
	el: '#app',
	vuetify: new Vuetify(opts)
})
